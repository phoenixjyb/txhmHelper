package com.txhmhelper.odds

import com.txhmhelper.model.Card
import com.txhmhelper.model.BoardState
import com.txhmhelper.model.Rank
import com.txhmhelper.model.Suit
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class EquityCalculatorTest {
    @Test
    fun rankedEvaluatorUsesKickersForPairHands() {
        val evaluator = RankedHandEvaluator()
        val acesWithKing = evaluator.evaluate(cards("As", "Ad", "Kc", "9h", "7s", "4d", "2c"))
        val acesWithQueen = evaluator.evaluate(cards("Ah", "Ac", "Qc", "9d", "7h", "4s", "2d"))

        assertTrue(acesWithKing > acesWithQueen)
    }

    @Test
    fun wheelStraightIsRecognized() {
        val evaluator = RankedHandEvaluator()
        val wheel = evaluator.evaluate(cards("As", "2d", "3c", "4h", "5s", "Kd", "Qc"))

        assertTrue(wheel.type.name == "STRAIGHT")
        assertTrue(wheel.kickers.single() == 5)
    }

    @Test
    fun multiwayEquityCountsEverySimulation() = runBlocking {
        val result = EquityCalculator().compute(
            state = BoardState(
                hole = cards("As", "Kd"),
                community = cards("Jh", "Td", "2c", "9s", "4d")
            ),
            players = 4,
            maxSamples = 100,
            timeBudgetMs = 1_000
        )

        assertEquals(4, result.players)
        assertEquals(result.samples, result.wins + result.ties + result.losses)
        assertTrue(result.equity in 0.0..1.0)
    }

    private fun cards(vararg ids: String): List<Card> = ids.map { id ->
        val rank = Rank.fromLabel(id.take(1))!!
        val suit = when (id.last()) {
            's' -> Suit.SPADES
            'h' -> Suit.HEARTS
            'd' -> Suit.DIAMONDS
            else -> Suit.CLUBS
        }
        Card(rank, suit)
    }
}
