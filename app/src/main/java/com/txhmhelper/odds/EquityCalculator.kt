package com.txhmhelper.odds

import com.txhmhelper.model.BoardState
import com.txhmhelper.model.Card
import com.txhmhelper.model.HandType
import com.txhmhelper.model.Rank
import com.txhmhelper.model.Suit
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.random.Random

data class EquityResult(
    val players: Int,
    val winProbability: Double,
    val tieProbability: Double,
    val equity: Double,
    val wins: Int,
    val ties: Int,
    val losses: Int,
    val samples: Int
)

/** Monte Carlo equity against uniformly random unknown opponent hands. */
class EquityCalculator(
    private val evaluator: RankedHandEvaluator = RankedHandEvaluator(),
    private val dispatcher: CoroutineDispatcher = Dispatchers.Default,
    private val random: Random = Random.Default
) {
    suspend fun compute(
        state: BoardState,
        players: Int,
        maxSamples: Int,
        timeBudgetMs: Long
    ): EquityResult = withContext(dispatcher) {
        require(players in 2..9) { "Players must be between 2 and 9." }
        require(state.hole.none { it == null }) { "Hero hole cards are required." }

        val deck = fullDeck().filterNot { it in state.usedCards() }
        val missingBoard = state.community.count { it == null }
        val opponents = players - 1
        val cardsNeeded = missingBoard + opponents * 2
        require(cardsNeeded <= deck.size) { "Not enough remaining cards." }

        var wins = 0
        var ties = 0
        var losses = 0
        var equityTotal = 0.0
        var samples = 0
        val startedAt = System.currentTimeMillis()

        while (samples < maxSamples) {
            if (samples > 0 && System.currentTimeMillis() - startedAt >= timeBudgetMs) break
            val draw = deck.shuffled(random).take(cardsNeeded)
            var drawIndex = 0
            val board = state.community.map { card -> card ?: draw[drawIndex++] }
            val opponentHands = List(opponents) {
                listOf(draw[drawIndex++], draw[drawIndex++])
            }
            val heroValue = evaluator.evaluate(state.hole.filterNotNull() + board)
            val opponentValues = opponentHands.map { evaluator.evaluate(it + board) }
            val bestValue = (listOf(heroValue) + opponentValues).maxOrNull()!!

            if (heroValue < bestValue) {
                losses++
            } else {
                val winners = 1 + opponentValues.count { it == heroValue }
                if (winners == 1) wins++ else ties++
                equityTotal += 1.0 / winners
            }
            samples++
        }

        EquityResult(
            players = players,
            winProbability = wins.rateOf(samples),
            tieProbability = ties.rateOf(samples),
            equity = if (samples == 0) 0.0 else equityTotal / samples,
            wins = wins,
            ties = ties,
            losses = losses,
            samples = samples
        )
    }

    private fun fullDeck(): List<Card> =
        Suit.entries.flatMap { suit -> Rank.entries.map { rank -> Card(rank, suit) } }
}

private fun Int.rateOf(total: Int): Double = if (total == 0) 0.0 else toDouble() / total

data class HandValue(val type: HandType, val kickers: List<Int>) : Comparable<HandValue> {
    override fun compareTo(other: HandValue): Int {
        val typeComparison = type.ordinal.compareTo(other.type.ordinal)
        if (typeComparison != 0) return typeComparison
        for (index in kickers.indices) {
            val kickerComparison = kickers[index].compareTo(other.kickers[index])
            if (kickerComparison != 0) return kickerComparison
        }
        return 0
    }
}

class RankedHandEvaluator {
    fun evaluate(cards: List<Card>): HandValue {
        require(cards.size == 7) { "Expected seven cards, got ${cards.size}." }
        var best: HandValue? = null
        for (a in 0 until 3) {
            for (b in a + 1 until 4) {
                for (c in b + 1 until 5) {
                    for (d in c + 1 until 6) {
                        for (e in d + 1 until 7) {
                            val value = evaluateFive(listOf(cards[a], cards[b], cards[c], cards[d], cards[e]))
                            if (best == null || value > best) best = value
                        }
                    }
                }
            }
        }
        return checkNotNull(best)
    }

    private fun evaluateFive(cards: List<Card>): HandValue {
        val ranks = cards.map { it.rank.value }.sortedDescending()
        val counts = ranks.groupingBy { it }.eachCount()
        val groups = counts.entries.sortedWith(compareByDescending<Map.Entry<Int, Int>> { it.value }.thenByDescending { it.key })
        val isFlush = cards.map { it.suit }.distinct().size == 1
        val straightHigh = straightHigh(counts.keys.sortedDescending())

        return when {
            isFlush && straightHigh != null -> HandValue(HandType.STRAIGHT_FLUSH, listOf(straightHigh))
            groups.first().value == 4 -> HandValue(HandType.QUADS, listOf(groups.first().key, groups[1].key))
            groups[0].value == 3 && groups[1].value == 2 -> HandValue(HandType.FULL_HOUSE, listOf(groups[0].key, groups[1].key))
            isFlush -> HandValue(HandType.FLUSH, ranks)
            straightHigh != null -> HandValue(HandType.STRAIGHT, listOf(straightHigh))
            groups.first().value == 3 -> HandValue(HandType.TRIPS, listOf(groups[0].key) + groups.drop(1).map { it.key })
            groups[0].value == 2 && groups[1].value == 2 -> HandValue(HandType.TWO_PAIR, listOf(groups[0].key, groups[1].key, groups[2].key))
            groups.first().value == 2 -> HandValue(HandType.PAIR, listOf(groups[0].key) + groups.drop(1).map { it.key })
            else -> HandValue(HandType.HIGH_CARD, ranks)
        }
    }

    private fun straightHigh(ranks: List<Int>): Int? {
        if (ranks.size != 5) return null
        if (ranks == listOf(14, 5, 4, 3, 2)) return 5
        return ranks.first().takeIf { ranks.zipWithNext().all { (a, b) -> a - b == 1 } }
    }
}
