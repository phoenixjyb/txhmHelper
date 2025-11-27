package com.txhmhelper.odds

import com.txhmhelper.model.BoardState
import com.txhmhelper.model.Card
import com.txhmhelper.model.HandType
import com.txhmhelper.model.Rank
import com.txhmhelper.model.Stage
import com.txhmhelper.model.Suit
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.sqrt
import kotlin.random.Random

data class HandProb(
    val hand: HandType,
    val probability: Double,
    val count: Int,
    val samples: Int,
    val standardError: Double? = null
)

data class OddsResult(
    val mode: OddsMode,
    val handProbs: List<HandProb>,
    val samples: Int
)

enum class OddsMode { MONTE_CARLO, EXACT }

enum class Precision(val samples: Int) {
    FAST(80_000),
    HIGH(320_000)
}

class OddsCalculator(
    private val evaluator: HandEvaluator = SimpleHandEvaluator(),
    private val dispatcher: CoroutineDispatcher = Dispatchers.Default,
    private val rng: Random = Random.Default
    ) {

    suspend fun compute(state: BoardState, precision: Precision, timeBudgetMs: Long = 250L): OddsResult =
        withContext(dispatcher) {
            if (state.hole.any { it == null }) {
                return@withContext OddsResult(
                    mode = OddsMode.MONTE_CARLO,
                    handProbs = emptyList(),
                    samples = 0
                )
            }
            val remainingDeck = fullDeck().filterNot { state.usedCards().contains(it) }
            val missingCommunity = state.community.count { it == null }
            return@withContext when (state.stage()) {
                Stage.PREFLOP -> monteCarlo(state, remainingDeck, missingCommunity, precision.samples, timeBudgetMs)
                Stage.FLOP, Stage.TURN -> exactEnumerate(state, remainingDeck, missingCommunity)
                Stage.RIVER -> exactAtRiver(state)
            }
        }

    private fun monteCarlo(
        state: BoardState,
        deck: List<Card>,
        missingCommunity: Int,
        samples: Int,
        timeBudgetMs: Long
    ): OddsResult {
        val counters = HandType.entries.associateWith { 0 }.toMutableMap()
        var iterations = 0
        val start = System.currentTimeMillis()

        val tempCommunity = state.community.toMutableList()

        while (iterations < samples) {
            if (System.currentTimeMillis() - start > timeBudgetMs) break
            val draw = drawCards(deck, missingCommunity)
            var drawIndex = 0
            tempCommunity.indices.forEach { idx ->
                tempCommunity[idx] = state.community[idx] ?: draw[drawIndex++]
            }
            val allCards = (state.hole.filterNotNull() + tempCommunity.filterNotNull())
            val best = evaluator.evaluate7(allCards)
            counters[best] = counters.getValue(best) + 1
            iterations++
        }

        val probs = counters.entries.map { (hand, count) ->
            val p = if (iterations == 0) 0.0 else count.toDouble() / iterations.toDouble()
            HandProb(
                hand = hand,
                probability = p,
                count = count,
                samples = iterations,
                standardError = if (iterations == 0) null else sqrt(p * (1 - p) / iterations)
            )
        }.sortedByDescending { it.probability }

        return OddsResult(mode = OddsMode.MONTE_CARLO, handProbs = probs, samples = iterations)
    }

    private fun exactEnumerate(
        state: BoardState,
        deck: List<Card>,
        missingCommunity: Int
    ): OddsResult {
        val counters = HandType.entries.associateWith { 0 }.toMutableMap()
        var iterations = 0

        fun evaluateWith(picks: List<Card>) {
            var pickIndex = 0
            val completedCommunity = state.community.map { card ->
                card ?: picks[pickIndex++]
            }
            val best = evaluator.evaluate7(state.hole.filterNotNull() + completedCommunity.filterNotNull())
            counters[best] = counters.getValue(best) + 1
            iterations++
        }

        when (missingCommunity) {
            0 -> evaluateWith(emptyList())
            1 -> {
                for (i in deck.indices) {
                    evaluateWith(listOf(deck[i]))
                }
            }
            2 -> {
                for (i in 0 until deck.size - 1) {
                    for (j in i + 1 until deck.size) {
                        evaluateWith(listOf(deck[i], deck[j]))
                    }
                }
            }
            else -> {
                // Should not occur post-flop, but handled defensively.
                val draw = drawCards(deck, missingCommunity)
                evaluateWith(draw)
            }
        }

        val probs = counters.entries.map { (hand, count) ->
            val p = if (iterations == 0) 0.0 else count.toDouble() / iterations.toDouble()
            HandProb(hand = hand, probability = p, count = count, samples = iterations)
        }.sortedByDescending { it.probability }

        return OddsResult(mode = OddsMode.EXACT, handProbs = probs, samples = iterations)
    }

    private fun exactAtRiver(state: BoardState): OddsResult {
        val best = evaluator.evaluate7(state.hole.filterNotNull() + state.community.filterNotNull())
        val probs = HandType.entries.map { hand ->
            HandProb(
                hand = hand,
                probability = if (hand == best) 1.0 else 0.0,
                count = if (hand == best) 1 else 0,
                samples = 1
            )
        }.sortedByDescending { it.probability }
        return OddsResult(mode = OddsMode.EXACT, handProbs = probs, samples = 1)
    }

    private fun drawCards(deck: List<Card>, needed: Int): List<Card> {
        if (needed <= 0) return emptyList()
        val mutableDeck = deck.toMutableList()
        mutableDeck.shuffle(rng)
        return mutableDeck.take(needed)
    }

    private fun fullDeck(): List<Card> =
        Suit.entries.flatMap { suit -> Rank.entries.map { rank -> Card(rank, suit) } }
}

interface HandEvaluator {
    fun evaluate7(cards: List<Card>): HandType
}

class SimpleHandEvaluator : HandEvaluator {
    override fun evaluate7(cards: List<Card>): HandType {
        require(cards.size == 7) { "Expected 7 cards, got ${cards.size}" }
        var best = HandType.HIGH_CARD
        for (a in 0 until 3) {
            for (b in a + 1 until 4) {
                for (c in b + 1 until 5) {
                    for (d in c + 1 until 6) {
                        for (e in d + 1 until 7) {
                            val subset = listOf(cards[a], cards[b], cards[c], cards[d], cards[e])
                            val type = evaluate5(subset)
                            if (strength(type) > strength(best)) {
                                best = type
                            }
                        }
                    }
                }
            }
        }
        return best
    }

    private fun evaluate5(cards: List<Card>): HandType {
        val suits = cards.groupingBy { it.suit }.eachCount()
        val rankCounts = cards.groupingBy { it.rank }.eachCount()
        val isFlush = suits.values.any { it == 5 }

        val rankValues = rankCounts.keys.map { it.value }.sorted()
        val distinctRanks = rankValues.distinct()

        val isWheel = distinctRanks == listOf(2, 3, 4, 5, 14)
        val isStraight = when {
            distinctRanks.size != 5 -> false
            isWheel -> true
            else -> distinctRanks.zipWithNext().all { (a, b) -> b - a == 1 }
        }

        val counts = rankCounts.values.sortedDescending()
        val pairCount = rankCounts.values.count { it == 2 }

        return when {
            isStraight && isFlush -> HandType.STRAIGHT_FLUSH
            counts.first() == 4 -> HandType.QUADS
            counts.first() == 3 && pairCount == 1 -> HandType.FULL_HOUSE
            isFlush -> HandType.FLUSH
            isStraight -> HandType.STRAIGHT
            counts.first() == 3 -> HandType.TRIPS
            pairCount >= 2 -> HandType.TWO_PAIR
            pairCount == 1 -> HandType.PAIR
            else -> HandType.HIGH_CARD
        }
    }

    private fun strength(type: HandType): Int = when (type) {
        HandType.HIGH_CARD -> 1
        HandType.PAIR -> 2
        HandType.TWO_PAIR -> 3
        HandType.TRIPS -> 4
        HandType.STRAIGHT -> 5
        HandType.FLUSH -> 6
        HandType.FULL_HOUSE -> 7
        HandType.QUADS -> 8
        HandType.STRAIGHT_FLUSH -> 9
    }
}
