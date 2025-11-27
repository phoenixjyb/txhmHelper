package com.txhmhelper.model

enum class Suit { SPADES, HEARTS, DIAMONDS, CLUBS }

enum class Rank(val label: String, val value: Int) {
    A("A", 14), TWO("2", 2), THREE("3", 3), FOUR("4", 4), FIVE("5", 5), SIX("6", 6), SEVEN("7", 7),
    EIGHT("8", 8), NINE("9", 9), TEN("T", 10), J("J", 11), Q("Q", 12), K("K", 13);

    companion object {
        fun fromLabel(label: String): Rank? = entries.firstOrNull { it.label.equals(label, ignoreCase = true) }
    }
}

data class Card(val rank: Rank, val suit: Suit) {
    val id: String = "${rank.label}${suit.name.first()}"
}

data class BoardState(
    val hole: List<Card?> = listOf(null, null),
    val community: List<Card?> = List(5) { null }
) {
    fun usedCards(): Set<Card> = (hole + community).filterNotNull().toSet()

    fun stage(): Stage = when (community.count { it != null }) {
        0, 1, 2 -> Stage.PREFLOP
        3 -> Stage.FLOP
        4 -> Stage.TURN
        else -> Stage.RIVER
    }

    fun nextTarget(): TargetSlot =
        hole.indexOfFirst { it == null }.takeIf { it >= 0 }?.let { TargetSlot.Hole(it) }
            ?: community.indexOfFirst { it == null }.takeIf { it >= 0 }?.let { TargetSlot.Community(it) }
            ?: TargetSlot.Hole(0)
}

enum class Stage { PREFLOP, FLOP, TURN, RIVER }

sealed class TargetSlot {
    data class Hole(val index: Int) : TargetSlot()
    data class Community(val index: Int) : TargetSlot()
}

enum class HandType {
    HIGH_CARD, PAIR, TWO_PAIR, TRIPS, STRAIGHT, FLUSH, FULL_HOUSE, QUADS, STRAIGHT_FLUSH
}
