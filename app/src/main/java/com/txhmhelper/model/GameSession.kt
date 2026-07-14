package com.txhmhelper.model

import kotlin.math.max

private const val ACTION_EPSILON = 1e-6

enum class GameStreet(val label: String) {
    PREFLOP("Preflop"),
    FLOP("Flop"),
    TURN("Turn"),
    RIVER("River");

    fun next(): GameStreet? = entries.getOrNull(ordinal + 1)
}

enum class PlayerActionType(val label: String) {
    CHECK("Check"),
    BET("Bet to"),
    CALL("Call"),
    RAISE("Raise to"),
    FOLD("Fold"),
    ALL_IN("All-in")
}

data class TablePlayer(
    val id: Int,
    val name: String,
    val stackBb: Double = 100.0,
    val streetCommittedBb: Double = 0.0,
    val isInHand: Boolean = true
)

data class RecordedAction(
    val street: GameStreet,
    val playerId: Int,
    val playerName: String,
    val type: PlayerActionType,
    val amountBb: Double,
    val potAfterBb: Double
) {
    fun display(): String = when (type) {
        PlayerActionType.CHECK, PlayerActionType.FOLD -> "$playerName ${type.label.lowercase()}"
        PlayerActionType.CALL -> "$playerName calls ${amountBb.formatBb()}"
        PlayerActionType.ALL_IN -> "$playerName all-in to ${amountBb.formatBb()}"
        else -> "$playerName ${type.label.lowercase()} ${amountBb.formatBb()}"
    }
}

data class GameSession(
    val street: GameStreet = GameStreet.PREFLOP,
    val players: List<TablePlayer> = createTablePlayers(2),
    val potBb: Double = 0.0,
    val actions: List<RecordedAction> = emptyList(),
    val dealerPlayerId: Int = 0,
    val selectedPlayerId: Int = 0
) {
    val playersInHand: Int get() = players.count { it.isInHand }
    val toCallBb: Double get() = players.filter { it.isInHand }.maxOfOrNull { it.streetCommittedBb } ?: 0.0
    val selectedPlayer: TablePlayer? get() = players.firstOrNull { it.id == selectedPlayerId && it.isInHand }
    val currentStreetActions: List<RecordedAction> get() = actions.filter { it.street == street }
    val potBeforeCurrentStreetBb: Double get() =
        (potBb - players.sumOf { it.streetCommittedBb }).coerceAtLeast(0.0)
    val effectiveStackAtCurrentStreetBb: Double get() =
        players.filter { it.isInHand }.minOfOrNull { it.stackBb + it.streetCommittedBb } ?: 0.0

    val isCurrentStreetComplete: Boolean
        get() {
            val streetActions = currentStreetActions
            val last = streetActions.lastOrNull()?.type ?: return false
            return last == PlayerActionType.CALL ||
                last == PlayerActionType.FOLD ||
                (streetActions.size >= 2 && streetActions.takeLast(2).all { it.type == PlayerActionType.CHECK })
        }

    fun selectPlayer(playerId: Int): GameSession {
        require(players.any { it.id == playerId && it.isInHand }) { "Select a player still in the hand." }
        return copy(selectedPlayerId = playerId)
    }

    fun recordAction(type: PlayerActionType, amountToBb: Double? = null): GameSession {
        val player = selectedPlayer ?: throw IllegalArgumentException("Select a player still in the hand.")
        if (playersInHand < 2) throw IllegalArgumentException("The hand is already finished.")
        val requiredToCall = max(0.0, toCallBb - player.streetCommittedBb)
        val target = when (type) {
            PlayerActionType.CHECK -> {
                require(requiredToCall <= ACTION_EPSILON) { "${player.name} must call, raise, or fold." }
                player.streetCommittedBb
            }
            PlayerActionType.CALL -> {
                require(requiredToCall > ACTION_EPSILON) { "Nothing to call; use check." }
                toCallBb
            }
            PlayerActionType.BET -> {
                require(toCallBb <= ACTION_EPSILON) { "A bet is already open; use raise, call, or fold." }
                requireAmount(amountToBb, player, player.streetCommittedBb)
            }
            PlayerActionType.RAISE -> {
                require(toCallBb > ACTION_EPSILON) { "No bet is open; use bet instead." }
                requireAmount(amountToBb, player, toCallBb)
            }
            PlayerActionType.ALL_IN -> player.streetCommittedBb + player.stackBb
            PlayerActionType.FOLD -> player.streetCommittedBb
        }
        if (type == PlayerActionType.ALL_IN && target <= player.streetCommittedBb + ACTION_EPSILON) {
            throw IllegalArgumentException("${player.name} has no chips left.")
        }
        val delta = target - player.streetCommittedBb
        val updatedPlayers = players.map {
            when {
                it.id != player.id -> it
                type == PlayerActionType.FOLD -> it.copy(isInHand = false)
                else -> it.copy(stackBb = (it.stackBb - delta).coerceAtLeast(0.0), streetCommittedBb = target)
            }
        }
        val updatedPot = potBb + delta
        val nextPlayer = nextPlayerForAction(updatedPlayers, player.id)
        return copy(
            players = updatedPlayers,
            potBb = updatedPot,
            actions = actions + RecordedAction(street, player.id, player.name, type, target, updatedPot),
            selectedPlayerId = nextPlayer.id
        )
    }

    fun advanceStreet(): GameSession {
        val nextStreet = street.next() ?: throw IllegalArgumentException("River is the final street.")
        val active = players.filter { it.isInHand }
        require(active.size >= 2) { "The hand is already finished." }
        return copy(
            street = nextStreet,
            players = players.map { it.copy(streetCommittedBb = 0.0) },
            selectedPlayerId = nextClockwiseActive(players, dealerPlayerId).id
        )
    }

    fun startNextHand(): GameSession {
        val resetPlayers = players.map { player ->
            player.copy(streetCommittedBb = 0.0, isInHand = player.stackBb > ACTION_EPSILON)
        }
        val nextDealer = nextClockwiseActive(resetPlayers, dealerPlayerId).id
        return copy(
            street = GameStreet.PREFLOP,
            players = resetPlayers,
            potBb = 0.0,
            actions = emptyList(),
            dealerPlayerId = nextDealer,
            selectedPlayerId = nextClockwiseActive(resetPlayers, nextDealer).id
        )
    }

    companion object {
        fun create(playerCount: Int, startingStackBb: Double = 100.0): GameSession {
            require(playerCount in 2..9) { "Players must be between 2 and 9." }
            require(startingStackBb > 0) { "Starting stack must be positive." }
            return GameSession(players = createTablePlayers(playerCount, startingStackBb))
        }

        private fun createTablePlayers(playerCount: Int, stackBb: Double = 100.0): List<TablePlayer> {
            val shuffledNames = animalNames.shuffled()
            return List(playerCount) { index ->
                TablePlayer(index, shuffledNames[index], stackBb)
            }
        }
    }
}

private val animalNames = listOf(
    "Aardvark",
    "Badger",
    "Cheetah",
    "Dolphin",
    "Elephant",
    "Falcon",
    "Gecko",
    "Hedgehog",
    "Ibex"
)

private fun requireAmount(amount: Double?, player: TablePlayer, minimumExclusive: Double): Double {
    require(amount != null && amount.isFinite()) { "Enter an amount in BB." }
    require(amount > minimumExclusive + ACTION_EPSILON) { "Amount must be above ${minimumExclusive.formatBb()}." }
    require(amount <= player.streetCommittedBb + player.stackBb + ACTION_EPSILON) { "Amount exceeds ${player.name}'s stack." }
    return amount
}

private fun nextPlayerForAction(players: List<TablePlayer>, afterPlayerId: Int): TablePlayer {
    val start = players.indexOfFirst { it.id == afterPlayerId }
    val highestCommitment = players.filter { it.isInHand }.maxOfOrNull { it.streetCommittedBb } ?: 0.0
    for (offset in 1..players.size) {
        val candidate = players[(start + offset) % players.size]
        if (candidate.isInHand && candidate.streetCommittedBb + ACTION_EPSILON < highestCommitment) {
            return candidate
        }
    }
    for (offset in 1..players.size) {
        val candidate = players[(start + offset) % players.size]
        if (candidate.isInHand) return candidate
    }
    return players.first { it.id == afterPlayerId }
}

private fun nextClockwiseActive(players: List<TablePlayer>, afterPlayerId: Int): TablePlayer {
    val start = players.indexOfFirst { it.id == afterPlayerId }
    for (offset in 1..players.size) {
        val candidate = players[(start + offset) % players.size]
        if (candidate.isInHand) return candidate
    }
    return players.first { it.id == afterPlayerId }
}

private fun Double.formatBb(): String = if (this % 1.0 == 0.0) "${toInt()}bb" else "${"%.1f".format(this)}bb"
