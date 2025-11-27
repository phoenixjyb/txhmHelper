package com.txhmhelper.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.txhmhelper.model.BoardState
import com.txhmhelper.model.Card
import com.txhmhelper.model.Stage
import com.txhmhelper.model.TargetSlot
import com.txhmhelper.odds.OddsCalculator
import com.txhmhelper.odds.OddsResult
import com.txhmhelper.odds.Precision
import com.txhmhelper.model.HandType
import com.txhmhelper.gto.GtoRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HandOddsUiState(
    val boardState: BoardState = BoardState(),
    val targetSlot: TargetSlot = TargetSlot.Hole(0),
    val odds: OddsResult? = null,
    val isComputing: Boolean = false,
    val precision: Precision = Precision.FAST,
    val recommendation: String? = null,
    val error: String? = null
)

class HandOddsViewModel(
    private val calculator: OddsCalculator = OddsCalculator(),
    private val gtoRepository: GtoRepository = GtoRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(HandOddsUiState())
    val uiState = _uiState.asStateFlow()

    private var computeJob: Job? = null

    fun selectSlot(slot: TargetSlot) {
        _uiState.update { it.copy(targetSlot = slot, error = null) }
    }

    fun onCardChosen(card: Card) {
        val current = _uiState.value
        val cardAlreadyInSlot = when (val slot = current.targetSlot) {
            is TargetSlot.Hole -> current.boardState.hole[slot.index]
            is TargetSlot.Community -> current.boardState.community[slot.index]
        }
        if (cardAlreadyInSlot == card) return
        if (current.boardState.usedCards().contains(card)) {
            _uiState.update { it.copy(error = "Card already used") }
            return
        }
        val updatedBoard = setCard(current.boardState, current.targetSlot, card)
        val nextTarget = updatedBoard.nextTarget()
        _uiState.update {
            it.copy(
                boardState = updatedBoard,
                targetSlot = nextTarget,
                error = null
            )
        }
        scheduleCompute()
    }

    fun clearSlot(slot: TargetSlot) {
        val updatedBoard = when (slot) {
            is TargetSlot.Hole -> _uiState.value.boardState.copy(
                hole = _uiState.value.boardState.hole.toMutableList().also { it[slot.index] = null }
            )
            is TargetSlot.Community -> _uiState.value.boardState.copy(
                community = _uiState.value.boardState.community.toMutableList().also { it[slot.index] = null }
            )
        }
        _uiState.update {
            it.copy(
                boardState = updatedBoard,
                targetSlot = slot,
                odds = if (updatedBoard.hole.any { card -> card == null }) null
                else if (updatedBoard.stage() == Stage.PREFLOP) null
                else it.odds
            )
        }
        scheduleCompute()
    }

    fun reset() {
        _uiState.value = HandOddsUiState()
    }

    fun setPrecision(precision: Precision) {
        if (_uiState.value.precision == precision) return
        _uiState.update { it.copy(precision = precision) }
        scheduleCompute()
    }

    private fun scheduleCompute() {
        val current = _uiState.value
        if (current.boardState.hole.any { it == null }) return

        computeJob?.cancel()
        computeJob = viewModelScope.launch {
            delay(180)
            _uiState.update { it.copy(isComputing = true, error = null) }
            val budget = if (_uiState.value.precision == Precision.FAST) 250L else 800L
            val result = calculator.compute(_uiState.value.boardState, _uiState.value.precision, budget)
            val reco = recommendationFor(result, _uiState.value.boardState.stage())
            _uiState.update { it.copy(isComputing = false, odds = result, recommendation = reco) }
            fetchGtoAdvice()
        }
    }

    private fun setCard(board: BoardState, slot: TargetSlot, card: Card): BoardState =
        when (slot) {
            is TargetSlot.Hole -> board.copy(
                hole = board.hole.toMutableList().also { it[slot.index] = card }
            )
            is TargetSlot.Community -> board.copy(
                community = board.community.toMutableList().also { it[slot.index] = card }
            )
        }

    private fun recommendationFor(result: OddsResult?, stage: Stage): String {
        if (result == null || result.handProbs.isEmpty()) return "Select cards to see advice."
        val top = result.handProbs.maxBy { it.probability }
        val strongProb = result.handProbs.filter { it.hand.ordinal >= HandType.FLUSH.ordinal }
            .sumOf { it.probability }
        val madeProb = result.handProbs.filter { it.hand.ordinal >= HandType.PAIR.ordinal }
            .sumOf { it.probability }

        return when (stage) {
            Stage.RIVER -> when {
                top.hand.ordinal >= HandType.FLUSH.ordinal -> "Bet/raise for value."
                top.hand.ordinal >= HandType.TWO_PAIR.ordinal -> "Value-bet thin or check/call."
                else -> "Mostly check/fold unless odds offered."
            }
            Stage.TURN -> when {
                strongProb > 0.45 -> "Bet/raise aggressively."
                strongProb > 0.25 || madeProb > 0.6 -> "Bet/call standard sizing."
                madeProb > 0.35 -> "Check/call small, fold to pressure."
                else -> "Mostly check/fold; bluff selectively."
            }
            Stage.FLOP -> when {
                strongProb > 0.4 -> "Bet/raise for value and protection."
                strongProb > 0.2 || madeProb > 0.55 -> "Bet/call; apply pressure on good turns."
                madeProb > 0.3 -> "Pot-control; check/call reasonable bets."
                else -> "Check/fold most of the time; bluff in good spots."
            }
            Stage.PREFLOP -> when {
                strongProb > 0.45 -> "Open/raise; continue aggression."
                strongProb > 0.25 -> "Open/call; avoid big pots out of position."
                else -> "Fold or limp only in multi-way pots."
            }
        }
    }

    private fun fetchGtoAdvice() {
        val state = _uiState.value.boardState
        if (state.hole.any { it == null }) return
        viewModelScope.launch {
            val response = gtoRepository.solve(
                stage = state.stage(),
                hole = state.hole.filterNotNull(),
                board = state.community
            )
            response?.let { res ->
                val bestAction = res.strategy.maxByOrNull { it.value }
                val text = bestAction?.let { "GTO: ${it.key} (${(it.value * 100).toInt()}%)" }
                    ?: "GTO mix available."
                _uiState.update { it.copy(recommendation = text) }
            }
        }
    }
}
