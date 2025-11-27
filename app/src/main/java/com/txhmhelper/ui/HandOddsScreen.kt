package com.txhmhelper.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.txhmhelper.model.Card
import com.txhmhelper.model.HandType
import com.txhmhelper.model.Rank
import com.txhmhelper.model.Suit
import com.txhmhelper.model.TargetSlot
import com.txhmhelper.odds.HandProb
import com.txhmhelper.odds.OddsMode
import com.txhmhelper.odds.Precision

@Composable
fun HandOddsScreen(viewModel: HandOddsViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    var pendingSuit by remember { mutableStateOf<Suit?>(null) }
    var pendingRank by remember { mutableStateOf<Rank?>(null) }

    LaunchedEffect(uiState.error) {
        uiState.error?.let { message ->
            snackbarHostState.showSnackbar(message, duration = SnackbarDuration.Short)
        }
    }

    LaunchedEffect(pendingSuit, pendingRank) {
        val suit = pendingSuit
        val rank = pendingRank
        if (suit != null && rank != null) {
            viewModel.onCardChosen(Card(rank, suit))
            pendingSuit = null
            pendingRank = null
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
        ) {
            OddsPanel(
                odds = uiState.odds?.handProbs ?: emptyList(),
                mode = uiState.odds?.mode,
                isComputing = uiState.isComputing,
                precision = uiState.precision,
                samples = uiState.odds?.samples ?: 0,
                recommendation = uiState.recommendation,
                onPrecisionChange = viewModel::setPrecision
            )

            CardBoard(
                hole = uiState.boardState.hole,
                community = uiState.boardState.community,
                target = uiState.targetSlot,
                onSlotSelected = viewModel::selectSlot,
                onClear = viewModel::clearSlot
            )

            CardPicker(
                pendingSuit = pendingSuit,
                pendingRank = pendingRank,
                onSuitSelected = { pendingSuit = it },
                onRankSelected = { pendingRank = it },
                onResetPicker = {
                    pendingSuit = null
                    pendingRank = null
                },
                usedCards = uiState.boardState.usedCards()
            )
        }
    }
}

@Composable
private fun OddsPanel(
    odds: List<HandProb>,
    mode: OddsMode?,
    isComputing: Boolean,
    precision: Precision,
    samples: Int,
    recommendation: String?,
    onPrecisionChange: (Precision) -> Unit
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Hand odds",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            mode?.let {
                Text(
                    text = if (it == OddsMode.MONTE_CARLO) "Monte Carlo" else "Exact",
                    style = MaterialTheme.typography.labelMedium
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AssistChip(
                    onClick = { onPrecisionChange(Precision.FAST) },
                    label = { Text("Fast") },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (precision == Precision.FAST) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent
                    )
                )
                AssistChip(
                    onClick = { onPrecisionChange(Precision.HIGH) },
                    label = { Text("High") },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (precision == Precision.HIGH) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent
                    )
                )
            }
        }
        recommendation?.let { reco ->
            Text(
                text = "Suggested line: $reco",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary
            )
        }
        if (isComputing) {
            Text(
                text = "Estimating...",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                style = MaterialTheme.typography.bodyMedium
            )
        } else if (odds.isEmpty()) {
            Text(
                text = "Pick your hole cards to see odds.",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                style = MaterialTheme.typography.bodyMedium
            )
        } else {
            Text(
                text = "Samples: $samples",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                style = MaterialTheme.typography.labelSmall
            )
        }
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp)
        ) {
            odds.forEach { item ->
                OddsRow(item, mode)
            }
        }
    }
}

@Composable
private fun OddsRow(prob: HandProb, mode: OddsMode?) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(text = prob.hand.displayName(), style = MaterialTheme.typography.bodyMedium)
            val comboLabel = when (mode) {
                OddsMode.EXACT -> "combos: ${prob.count}"
                OddsMode.MONTE_CARLO -> "hits: ${prob.count}/${prob.samples}"
                else -> null
            }
            comboLabel?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
        }
        Text(
            text = "${(prob.probability * 100).formatOneDecimal()}%",
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun CardBoard(
    hole: List<Card?>,
    community: List<Card?>,
    target: TargetSlot,
    onSlotSelected: (TargetSlot) -> Unit,
    onClear: (TargetSlot) -> Unit
) {
    val cardHeight = 90.dp

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp)
    ) {
        Text("Your hole cards", style = MaterialTheme.typography.titleMedium)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            (0 until 5).forEach { idx ->
                if (idx < hole.size) {
                    CardSlot(
                        label = "Hole ${idx + 1}",
                        card = hole[idx],
                        selected = target == TargetSlot.Hole(idx),
                        onClick = { onSlotSelected(TargetSlot.Hole(idx)) },
                        onClear = { onClear(TargetSlot.Hole(idx)) },
                        modifier = Modifier
                            .weight(1f)
                            .height(cardHeight)
                    )
                } else {
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(cardHeight)
                    )
                }
            }
        }
        Spacer(modifier = Modifier.size(12.dp))
        Text("Community", style = MaterialTheme.typography.titleMedium)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            community.forEachIndexed { index, card ->
                CardSlot(
                    label = labelForCommunity(index),
                    card = card,
                    selected = target == TargetSlot.Community(index),
                    onClick = { onSlotSelected(TargetSlot.Community(index)) },
                    onClear = { onClear(TargetSlot.Community(index)) },
                    modifier = Modifier
                        .weight(1f)
                        .height(cardHeight)
                )
            }
        }
    }
}

@Composable
private fun CardSlot(
    label: String,
    card: Card?,
    selected: Boolean,
    onClick: () -> Unit,
    onClear: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier
            .padding(vertical = 4.dp)
            .clickable { onClick() },
        tonalElevation = if (selected) 4.dp else 0.dp,
        shadowElevation = if (selected) 4.dp else 0.dp,
        color = if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f) else MaterialTheme.colorScheme.surfaceVariant
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(label, style = MaterialTheme.typography.labelSmall)
            Text(
                text = card?.let { "${it.rank.label}${suitSymbol(it.suit)}" } ?: "--",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold
            )
            if (card != null) {
                Text(
                    text = "Clear",
                    modifier = Modifier
                        .clickable { onClear() }
                        .padding(top = 4.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

@Composable
private fun CardPicker(
    pendingSuit: Suit?,
    pendingRank: Rank?,
    onSuitSelected: (Suit) -> Unit,
    onRankSelected: (Rank) -> Unit,
    onResetPicker: () -> Unit,
    usedCards: Set<Card>
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .background(MaterialTheme.colorScheme.surfaceVariant),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("Tap suit then rank", style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Suit.entries.forEach { suit ->
                val selected = pendingSuit == suit
                AssistChip(
                    onClick = { onSuitSelected(suit) },
                    label = { Text(suitSymbol(suit)) },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent
                    )
                )
            }
            Spacer(modifier = Modifier.weight(1f))
            OutlinedButton(
                onClick = onResetPicker,
                enabled = pendingSuit != null || pendingRank != null
            ) {
                Text("Reset picker")
            }
        }
        val topRow = listOf(Rank.A, Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX, Rank.SEVEN)
        val bottomRow = listOf(Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.J, Rank.Q, Rank.K)

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            topRow.forEach { rank ->
                val selected = pendingRank == rank
                val isUsedWithSelectedSuit = pendingSuit?.let { suit ->
                    usedCards.any { it.rank == rank && it.suit == suit }
                } ?: false
                AssistChip(
                    onClick = { if (!isUsedWithSelectedSuit) onRankSelected(rank) },
                    label = { Text(rank.label) },
                    modifier = Modifier.weight(1f),
                    enabled = !isUsedWithSelectedSuit,
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent
                    )
                )
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            bottomRow.forEach { rank ->
                val selected = pendingRank == rank
                val isUsedWithSelectedSuit = pendingSuit?.let { suit ->
                    usedCards.any { it.rank == rank && it.suit == suit }
                } ?: false
                AssistChip(
                    onClick = { if (!isUsedWithSelectedSuit) onRankSelected(rank) },
                    label = { Text(rank.label) },
                    modifier = Modifier.weight(1f),
                    enabled = !isUsedWithSelectedSuit,
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent
                    )
                )
            }
            AssistChip(
                onClick = {},
                enabled = false,
                label = { Text("Win") },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

private fun labelForCommunity(index: Int): String = when (index) {
    0 -> "Flop 1"
    1 -> "Flop 2"
    2 -> "Flop 3"
    3 -> "Turn"
    else -> "River"
}

private fun suitSymbol(suit: Suit): String = when (suit) {
    Suit.SPADES -> "♠"
    Suit.HEARTS -> "♥"
    Suit.DIAMONDS -> "♦"
    Suit.CLUBS -> "♣"
}

private fun HandType.displayName(): String = when (this) {
    HandType.HIGH_CARD -> "High Card"
    HandType.PAIR -> "One Pair"
    HandType.TWO_PAIR -> "Two Pair"
    HandType.TRIPS -> "Three of a Kind"
    HandType.STRAIGHT -> "Straight"
    HandType.FLUSH -> "Flush"
    HandType.FULL_HOUSE -> "Full House"
    HandType.QUADS -> "Four of a Kind"
    HandType.STRAIGHT_FLUSH -> "Straight Flush"
}

private fun Double.formatOneDecimal(): String = String.format("%.1f", this)
