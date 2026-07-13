package com.txhmhelper.gto

import com.txhmhelper.model.Card
import com.txhmhelper.model.Stage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class GtoRepository(
    private val service: GtoService = GtoClient.service
) {
    suspend fun solve(
        stage: Stage,
        hole: List<Card>,
        board: List<Card?>,
        pot: Double = 1.0,
        effectiveStack: Double = 100.0
    ): GtoSolveResponse = withContext(Dispatchers.IO) {
        val boardCards = board.filterNotNull()
        require(hole.size == 2) { "Exactly two hole cards are required." }
        val req = GtoSolveRequest(
            stage = stage,
            hole = hole.take(2).map { it.toApiId() },
            board = boardCards.map { it.toApiId() },
            pot = pot,
            effectiveStack = effectiveStack
        )
        service.solve(req)
    }
}

private fun Card.toApiId(): String {
    val suitLetter = when (suit) {
        com.txhmhelper.model.Suit.SPADES -> "s"
        com.txhmhelper.model.Suit.HEARTS -> "h"
        com.txhmhelper.model.Suit.DIAMONDS -> "d"
        com.txhmhelper.model.Suit.CLUBS -> "c"
    }
    return "${rank.label}$suitLetter"
}
