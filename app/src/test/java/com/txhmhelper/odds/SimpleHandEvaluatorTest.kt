package com.txhmhelper.odds

import com.txhmhelper.model.Card
import com.txhmhelper.model.HandType
import com.txhmhelper.model.Rank
import com.txhmhelper.model.Suit
import com.txhmhelper.odds.Precision
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test
import kotlin.random.Random

class SimpleHandEvaluatorTest {

    private val evaluator = SimpleHandEvaluator()

    @Test
    fun straightFlushWins() {
        val cards = listOf(
            c(Rank.NINE, Suit.HEARTS),
            c(Rank.TEN, Suit.HEARTS),
            c(Rank.J, Suit.HEARTS),
            c(Rank.Q, Suit.HEARTS),
            c(Rank.K, Suit.HEARTS),
            c(Rank.TWO, Suit.CLUBS),
            c(Rank.THREE, Suit.SPADES)
        )
        assertEquals(HandType.STRAIGHT_FLUSH, evaluator.evaluate7(cards))
    }

    @Test
    fun quadsDetected() {
        val cards = listOf(
            c(Rank.FIVE, Suit.HEARTS),
            c(Rank.FIVE, Suit.CLUBS),
            c(Rank.FIVE, Suit.DIAMONDS),
            c(Rank.FIVE, Suit.SPADES),
            c(Rank.A, Suit.HEARTS),
            c(Rank.K, Suit.CLUBS),
            c(Rank.TWO, Suit.SPADES)
        )
        assertEquals(HandType.QUADS, evaluator.evaluate7(cards))
    }

    @Test
    fun fullHouseDetected() {
        val cards = listOf(
            c(Rank.TEN, Suit.SPADES),
            c(Rank.TEN, Suit.HEARTS),
            c(Rank.TEN, Suit.CLUBS),
            c(Rank.A, Suit.DIAMONDS),
            c(Rank.A, Suit.CLUBS),
            c(Rank.FOUR, Suit.SPADES),
            c(Rank.SEVEN, Suit.HEARTS)
        )
        assertEquals(HandType.FULL_HOUSE, evaluator.evaluate7(cards))
    }

    @Test
    fun flushBeatsStraight() {
        val cards = listOf(
            c(Rank.TWO, Suit.HEARTS),
            c(Rank.SIX, Suit.HEARTS),
            c(Rank.NINE, Suit.HEARTS),
            c(Rank.J, Suit.HEARTS),
            c(Rank.K, Suit.HEARTS),
            c(Rank.THREE, Suit.SPADES),
            c(Rank.FOUR, Suit.CLUBS)
        )
        assertEquals(HandType.FLUSH, evaluator.evaluate7(cards))
    }

    @Test
    fun straightDetected() {
        val cards = listOf(
            c(Rank.FIVE, Suit.HEARTS),
            c(Rank.SIX, Suit.CLUBS),
            c(Rank.SEVEN, Suit.DIAMONDS),
            c(Rank.EIGHT, Suit.SPADES),
            c(Rank.NINE, Suit.CLUBS),
            c(Rank.K, Suit.HEARTS),
            c(Rank.TWO, Suit.SPADES)
        )
        assertEquals(HandType.STRAIGHT, evaluator.evaluate7(cards))
    }

    @Test
    fun tripsDetected() {
        val cards = listOf(
            c(Rank.Q, Suit.HEARTS),
            c(Rank.Q, Suit.DIAMONDS),
            c(Rank.Q, Suit.SPADES),
            c(Rank.FIVE, Suit.CLUBS),
            c(Rank.SEVEN, Suit.SPADES),
            c(Rank.NINE, Suit.CLUBS),
            c(Rank.J, Suit.HEARTS)
        )
        assertEquals(HandType.TRIPS, evaluator.evaluate7(cards))
    }

    @Test
    fun twoPairDetected() {
        val cards = listOf(
            c(Rank.A, Suit.HEARTS),
            c(Rank.A, Suit.CLUBS),
            c(Rank.K, Suit.DIAMONDS),
            c(Rank.K, Suit.SPADES),
            c(Rank.FIVE, Suit.HEARTS),
            c(Rank.THREE, Suit.CLUBS),
            c(Rank.TWO, Suit.SPADES)
        )
        assertEquals(HandType.TWO_PAIR, evaluator.evaluate7(cards))
    }

    @Test
    fun pairDetected() {
        val cards = listOf(
            c(Rank.J, Suit.HEARTS),
            c(Rank.J, Suit.CLUBS),
            c(Rank.FOUR, Suit.SPADES),
            c(Rank.SIX, Suit.DIAMONDS),
            c(Rank.NINE, Suit.CLUBS),
            c(Rank.TWO, Suit.HEARTS),
            c(Rank.THREE, Suit.DIAMONDS)
        )
        assertEquals(HandType.PAIR, evaluator.evaluate7(cards))
    }

    @Test
    fun highCardDetected() {
        val cards = listOf(
            c(Rank.A, Suit.HEARTS),
            c(Rank.K, Suit.CLUBS),
            c(Rank.EIGHT, Suit.DIAMONDS),
            c(Rank.SEVEN, Suit.SPADES),
            c(Rank.FOUR, Suit.CLUBS),
            c(Rank.THREE, Suit.HEARTS),
            c(Rank.TWO, Suit.DIAMONDS)
        )
        assertEquals(HandType.HIGH_CARD, evaluator.evaluate7(cards))
    }

    @Test
    fun computeSkipsWithoutHoleCards() = runBlocking {
        val calc = OddsCalculator(dispatcher = kotlinx.coroutines.Dispatchers.Unconfined, rng = Random(123))
        val result = calc.compute(com.txhmhelper.model.BoardState(), Precision.FAST)
        assertEquals(0, result.samples)
        assertEquals(0, result.handProbs.size)
    }

    private fun c(rank: Rank, suit: Suit) = Card(rank, suit)
}
