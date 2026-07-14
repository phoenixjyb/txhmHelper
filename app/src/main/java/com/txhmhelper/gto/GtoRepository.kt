package com.txhmhelper.gto

import com.txhmhelper.model.Card
import com.txhmhelper.model.GameSession
import com.txhmhelper.model.PlayerActionType
import com.txhmhelper.model.Stage
import kotlinx.coroutines.delay
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

    suspend fun solveTable(
        stage: Stage,
        hole: List<Card>,
        board: List<Card?>,
        session: GameSession
    ): GtoV1SolveResult = withContext(Dispatchers.IO) {
        val boardCards = board.filterNotNull()
        require(stage != Stage.PREFLOP) { "The bounded table solver starts postflop." }
        require(hole.size == 2) { "Exactly two hole cards are required." }
        require(session.players.size == 2 && session.playersInHand == 2) { "Table solving is heads-up only." }
        require(session.selectedPlayerId == 0) { "Select your seat when it is your turn." }
        require(!session.isCurrentStreetComplete) { "Advance the street after a completed betting line." }
        require(session.potBeforeCurrentStreetBb > 0.0) { "Record the preflop pot before requesting postflop advice." }

        val streetActions = session.currentStreetActions
        val heroPosition = if (streetActions.firstOrNull()?.playerId == 1) "ip" else "oop"
        val request = GtoTableSolveRequest(
            stage = stage.name.lowercase(),
            hole = hole.map { it.toApiId() },
            board = boardCards.map { it.toApiId() },
            potBeforeStreet = session.potBeforeCurrentStreetBb,
            effectiveStack = session.effectiveStackAtCurrentStreetBb,
            heroPosition = heroPosition,
            actions = streetActions.map { action ->
                GtoTableAction(
                    player = if (action.playerId == 0) "hero" else "villain",
                    type = action.type.toApiAction(),
                    amountTo = when (action.type) {
                        PlayerActionType.BET,
                        PlayerActionType.RAISE,
                        PlayerActionType.ALL_IN -> action.amountBb
                        else -> null
                    }
                )
            }
        )
        var job = service.createTableSolve(request)
        repeat(120) {
            when (job.status) {
                "complete" -> return@withContext requireNotNull(job.result)
                "failed" -> throw IllegalStateException(job.error ?: "The solver job failed.")
            }
            delay(250)
            job = service.getSolveJob(job.jobId)
        }
        throw IllegalStateException("The solver did not finish within 30 seconds.")
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

private fun PlayerActionType.toApiAction(): String = when (this) {
    PlayerActionType.CHECK -> "check"
    PlayerActionType.BET -> "bet"
    PlayerActionType.CALL -> "call"
    PlayerActionType.RAISE -> "raise"
    PlayerActionType.FOLD -> "fold"
    PlayerActionType.ALL_IN -> "all_in"
}
