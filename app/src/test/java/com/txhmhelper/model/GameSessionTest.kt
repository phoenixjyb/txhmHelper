package com.txhmhelper.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GameSessionTest {

    @Test
    fun createBuildsRequestedTableWithUniqueAnimalNames() {
        val session = GameSession.create(6)

        assertEquals(6, session.players.size)
        assertEquals(6, session.players.map { it.name }.toSet().size)
        assertTrue(session.players.all { it.name.isNotBlank() })
        assertEquals(100.0, session.players.first().stackBb, 0.0)
    }

    @Test
    fun betRaiseAndCallUpdatePotStacksAndNextActor() {
        val session = GameSession.create(3)
            .selectPlayer(0)
            .recordAction(PlayerActionType.BET, 5.0)
            .selectPlayer(1)
            .recordAction(PlayerActionType.RAISE, 15.0)
            .selectPlayer(0)
            .recordAction(PlayerActionType.CALL)

        assertEquals(30.0, session.potBb, 0.0)
        assertEquals(85.0, session.players[0].stackBb, 0.0)
        assertEquals(85.0, session.players[1].stackBb, 0.0)
        assertEquals(100.0, session.players[2].stackBb, 0.0)
        assertEquals(15.0, session.toCallBb, 0.0)
        assertEquals(2, session.selectedPlayerId)
    }

    @Test
    fun foldRemovesPlayerFromEquityOpponents() {
        val session = GameSession.create(3)
            .selectPlayer(2)
            .recordAction(PlayerActionType.FOLD)

        assertEquals(2, session.playersInHand)
        assertFalse(session.players[2].isInHand)
        assertEquals(0.0, session.potBb, 0.0)
    }

    @Test
    fun advancingStreetResetsOnlyStreetCommitments() {
        val session = GameSession.create(2)
            .recordAction(PlayerActionType.BET, 4.0)
            .recordAction(PlayerActionType.CALL)
            .advanceStreet()

        assertEquals(GameStreet.FLOP, session.street)
        assertEquals(8.0, session.potBb, 0.0)
        assertTrue(session.players.all { it.streetCommittedBb == 0.0 })
        assertEquals(1, session.selectedPlayerId)
    }

    @Test
    fun nextHandMovesDealerClockwiseAndRestoresFoldedPlayers() {
        val session = GameSession.create(3)
            .selectPlayer(1)
            .recordAction(PlayerActionType.FOLD)
            .startNextHand()

        assertEquals(1, session.dealerPlayerId)
        assertEquals(2, session.selectedPlayerId)
        assertEquals(GameStreet.PREFLOP, session.street)
        assertEquals(0.0, session.potBb, 0.0)
        assertTrue(session.players.all { it.isInHand })
        assertTrue(session.actions.isEmpty())
    }

    @Test(expected = IllegalArgumentException::class)
    fun checkIsRejectedWhenFacingABet() {
        GameSession.create(2)
            .recordAction(PlayerActionType.BET, 5.0)
            .recordAction(PlayerActionType.CHECK)
    }
}
