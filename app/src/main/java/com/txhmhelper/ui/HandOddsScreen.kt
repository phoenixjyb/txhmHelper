package com.txhmhelper.ui

import android.content.res.Configuration
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.txhmhelper.model.Card
import com.txhmhelper.model.GameSession
import com.txhmhelper.model.HandType
import com.txhmhelper.model.PlayerActionType
import com.txhmhelper.model.Rank
import com.txhmhelper.model.Suit
import com.txhmhelper.model.TargetSlot
import com.txhmhelper.odds.HandProb
import com.txhmhelper.odds.EquityResult
import com.txhmhelper.odds.OddsMode
import com.txhmhelper.odds.Precision
import kotlin.math.abs

@Composable
fun HandOddsScreen(viewModel: HandOddsViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val isLandscape = LocalConfiguration.current.orientation == Configuration.ORIENTATION_LANDSCAPE
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
        if (isLandscape) {
            LandscapeDashboard(
                modifier = Modifier.fillMaxSize().padding(padding),
                state = uiState,
                onPrecisionChange = viewModel::setPrecision,
                onPlayersChange = viewModel::setActivePlayers,
                onActionPlayerSelected = viewModel::selectActionPlayer,
                onRecordAction = viewModel::recordPlayerAction,
                onAdvanceStreet = viewModel::advanceActionStreet,
                onSlotSelected = viewModel::selectSlot,
                onClear = viewModel::clearSlot,
                pendingSuit = pendingSuit,
                pendingRank = pendingRank,
                onSuitSelected = { pendingSuit = it },
                onRankSelected = { pendingRank = it },
                onResetPicker = {
                    pendingSuit = null
                    pendingRank = null
                }
            )
        } else {
            PortraitDashboard(
                modifier = Modifier.fillMaxSize().padding(padding),
                state = uiState,
                onPrecisionChange = viewModel::setPrecision,
                onPlayersChange = viewModel::setActivePlayers,
                onActionPlayerSelected = viewModel::selectActionPlayer,
                onRecordAction = viewModel::recordPlayerAction,
                onAdvanceStreet = viewModel::advanceActionStreet,
                onSlotSelected = viewModel::selectSlot,
                onClear = viewModel::clearSlot,
                pendingSuit = pendingSuit,
                pendingRank = pendingRank,
                onSuitSelected = { pendingSuit = it },
                onRankSelected = { pendingRank = it },
                onResetPicker = {
                    pendingSuit = null
                    pendingRank = null
                }
            )
        }
    }
}

@Composable
private fun PortraitDashboard(
    modifier: Modifier,
    state: HandOddsUiState,
    onPrecisionChange: (Precision) -> Unit,
    onPlayersChange: (Int) -> Unit,
    onActionPlayerSelected: (Int) -> Unit,
    onRecordAction: (PlayerActionType, Double?) -> Unit,
    onAdvanceStreet: () -> Unit,
    onSlotSelected: (TargetSlot) -> Unit,
    onClear: (TargetSlot) -> Unit,
    pendingSuit: Suit?,
    pendingRank: Rank?,
    onSuitSelected: (Suit) -> Unit,
    onRankSelected: (Rank) -> Unit,
    onResetPicker: () -> Unit
) {
    FullTableDashboard(
        modifier = modifier,
        state = state,
        onPrecisionChange = onPrecisionChange,
        onPlayersChange = onPlayersChange,
        onActionPlayerSelected = onActionPlayerSelected,
        onRecordAction = onRecordAction,
        onAdvanceStreet = onAdvanceStreet,
        onSlotSelected = onSlotSelected,
        onClear = onClear,
        pendingSuit = pendingSuit,
        pendingRank = pendingRank,
        onSuitSelected = onSuitSelected,
        onRankSelected = onRankSelected,
        onResetPicker = onResetPicker
    )
}

@Composable
private fun LandscapeDashboard(
    modifier: Modifier,
    state: HandOddsUiState,
    onPrecisionChange: (Precision) -> Unit,
    onPlayersChange: (Int) -> Unit,
    onActionPlayerSelected: (Int) -> Unit,
    onRecordAction: (PlayerActionType, Double?) -> Unit,
    onAdvanceStreet: () -> Unit,
    onSlotSelected: (TargetSlot) -> Unit,
    onClear: (TargetSlot) -> Unit,
    pendingSuit: Suit?,
    pendingRank: Rank?,
    onSuitSelected: (Suit) -> Unit,
    onRankSelected: (Rank) -> Unit,
    onResetPicker: () -> Unit
) {
    FullTableDashboard(
        modifier = modifier,
        state = state,
        onPrecisionChange = onPrecisionChange,
        onPlayersChange = onPlayersChange,
        onActionPlayerSelected = onActionPlayerSelected,
        onRecordAction = onRecordAction,
        onAdvanceStreet = onAdvanceStreet,
        onSlotSelected = onSlotSelected,
        onClear = onClear,
        pendingSuit = pendingSuit,
        pendingRank = pendingRank,
        onSuitSelected = onSuitSelected,
        onRankSelected = onRankSelected,
        onResetPicker = onResetPicker
    )
}

@Composable
private fun FullTableDashboard(
    modifier: Modifier,
    state: HandOddsUiState,
    onPrecisionChange: (Precision) -> Unit,
    onPlayersChange: (Int) -> Unit,
    onActionPlayerSelected: (Int) -> Unit,
    onRecordAction: (PlayerActionType, Double?) -> Unit,
    onAdvanceStreet: () -> Unit,
    onSlotSelected: (TargetSlot) -> Unit,
    onClear: (TargetSlot) -> Unit,
    pendingSuit: Suit?,
    pendingRank: Rank?,
    onSuitSelected: (Suit) -> Unit,
    onRankSelected: (Rank) -> Unit,
    onResetPicker: () -> Unit
) {
    var showOdds by remember { mutableStateOf(false) }
    var showActions by remember { mutableStateOf(false) }
    var showPicker by remember { mutableStateOf(true) }
    Box(modifier = modifier) {
        PokerTableSurface(
            session = state.gameSession,
            hole = state.boardState.hole,
            community = state.boardState.community,
            target = state.targetSlot,
            onActionPlayerSelected = onActionPlayerSelected,
            onSlotSelected = onSlotSelected,
            onClear = onClear,
            modifier = Modifier.fillMaxSize()
        )

        if (showOdds) {
            Column(
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .width(300.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                OddsPanel(state, onPrecisionChange)
            }
        }
        if (showActions) {
            Column(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .width(320.dp)
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
            ) {
                GameContextPanel(
                    session = state.gameSession,
                    equity = state.equity,
                    isComputing = state.isComputing,
                    onPlayersChange = onPlayersChange,
                    onActionPlayerSelected = onActionPlayerSelected,
                    onRecordAction = onRecordAction,
                    onAdvanceStreet = onAdvanceStreet
                )
            }
        }
        if (showPicker) {
            DialCardPicker(
                pendingSuit = pendingSuit,
                pendingRank = pendingRank,
                usedCards = state.boardState.usedCards(),
                onSuitSelected = onSuitSelected,
                onRankSelected = onRankSelected,
                onResetPicker = onResetPicker,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(horizontal = 16.dp, vertical = 14.dp)
            )
        }

        Row(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 10.dp, end = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            OverlayToggle("Odds", showOdds) { showOdds = !showOdds }
            OverlayToggle("Actions", showActions) { showActions = !showActions }
            OverlayToggle("Cards", showPicker) { showPicker = !showPicker }
        }
    }
}

@Composable
private fun OverlayToggle(label: String, selected: Boolean, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = if (selected) PokerGold else PokerSeat,
        border = BorderStroke(1.dp, if (selected) PokerGold else Color.White.copy(alpha = 0.45f)),
        shadowElevation = 4.dp
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            color = if (selected) Color(0xFF1E241F) else Color.White,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun OddsPanel(
    state: HandOddsUiState,
    onPrecisionChange: (Precision) -> Unit
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Hand odds",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                state.odds?.mode?.let {
                    Text(
                        text = if (it == OddsMode.MONTE_CARLO) "Monte Carlo" else "Exact",
                        style = MaterialTheme.typography.labelMedium
                    )
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End
            ) {
                AssistChip(
                    onClick = { onPrecisionChange(Precision.FAST) },
                    label = { Text("Fast") },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (state.precision == Precision.FAST) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent
                    )
                )
                Spacer(modifier = Modifier.width(8.dp))
                AssistChip(
                    onClick = { onPrecisionChange(Precision.HIGH) },
                    label = { Text("High") },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (state.precision == Precision.HIGH) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent
                    )
                )
            }
        }
        state.recommendation?.let { reco ->
            Text(
                text = "Suggested line: $reco",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary
            )
        }
        when (state.gtoStatus) {
            GtoStatus.LOADING -> Text(
                text = "GTO: calculating...",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 2.dp),
                style = MaterialTheme.typography.labelMedium
            )
            GtoStatus.AVAILABLE -> Text(
                text = "GTO: ${state.gtoAdvice}",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 2.dp),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.tertiary
            )
            GtoStatus.UNAVAILABLE -> Text(
                text = "GTO: server unavailable",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 2.dp),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.error
            )
            GtoStatus.IDLE -> Unit
        }
        if (state.isComputing) {
            Text(
                text = "Estimating...",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                style = MaterialTheme.typography.bodyMedium
            )
        } else if (state.odds?.handProbs.isNullOrEmpty()) {
            Text(
                text = "Pick your hole cards to see odds.",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                style = MaterialTheme.typography.bodyMedium
            )
        } else {
            Text(
                text = "Samples: ${state.odds?.samples ?: 0}",
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                style = MaterialTheme.typography.labelSmall
            )
        }
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp)
        ) {
            state.odds?.handProbs?.forEach { item ->
                OddsRow(item, state.odds.mode)
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

private fun Double.formatBb(): String =
    if (this % 1.0 == 0.0) "${toInt()}bb" else "${"%.1f".format(this)}bb"

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun GameContextPanel(
    session: GameSession,
    equity: EquityResult?,
    isComputing: Boolean,
    onPlayersChange: (Int) -> Unit,
    onActionPlayerSelected: (Int) -> Unit,
    onRecordAction: (PlayerActionType, Double?) -> Unit,
    onAdvanceStreet: () -> Unit
) {
    var showActionDialog by remember { mutableStateOf(false) }
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Table context", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("Start game — players at table", style = MaterialTheme.typography.labelMedium)
            PlayerCountRow((2..5).toList(), session.players.size, onPlayersChange)
            PlayerCountRow((6..9).toList(), session.players.size, onPlayersChange)
            Text(
                text = "${session.street.label}  •  Pot ${session.potBb.formatBb()}  •  To call ${session.toCallBb.formatBb()}",
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = "${session.playersInHand}/${session.players.size} players remain",
                style = MaterialTheme.typography.labelSmall
            )

            Text("Tap a player, then record an action", style = MaterialTheme.typography.labelMedium)
            session.players.forEach { player ->
                FilterChip(
                    selected = player.id == session.selectedPlayerId,
                    enabled = player.isInHand,
                    onClick = { onActionPlayerSelected(player.id) },
                    label = {
                        Text(
                            "${player.name}: ${player.stackBb.formatBb()}  •  street ${player.streetCommittedBb.formatBb()}" +
                                if (player.isInHand) "" else "  •  folded"
                        )
                    },
                    modifier = Modifier.fillMaxWidth()
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = { showActionDialog = true },
                    enabled = session.selectedPlayer != null,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("${session.selectedPlayer?.name ?: "Player"} action")
                }
                OutlinedButton(
                    onClick = onAdvanceStreet,
                    enabled = session.street.next() != null && session.playersInHand >= 2,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Next street")
                }
            }
            if (session.actions.isEmpty()) {
                Text("Actions update pot and remaining stacks automatically.", style = MaterialTheme.typography.labelSmall)
            } else {
                Text("Action timeline", style = MaterialTheme.typography.labelMedium)
                session.actions.takeLast(5).forEach { action ->
                    Text("${action.street.label}: ${action.display()}  •  pot ${action.potAfterBb.formatBb()}", style = MaterialTheme.typography.labelSmall)
                }
            }

            when {
                isComputing -> Text("Equity: calculating...", style = MaterialTheme.typography.bodyMedium)
                equity != null -> {
                    Text(
                        text = "Equity: ${(equity.equity * 100).formatOneDecimal()}%",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Win ${(equity.winProbability * 100).formatOneDecimal()}%  Tie ${(equity.tieProbability * 100).formatOneDecimal()}%",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = "${equity.samples} Monte Carlo hands vs ${session.playersInHand - 1} random opponent${if (session.playersInHand == 2) "" else "s"}",
                        style = MaterialTheme.typography.labelSmall
                    )
                }
                session.players.firstOrNull()?.isInHand == false -> Text("Hero folded; equity stopped.", style = MaterialTheme.typography.bodyMedium)
                else -> Text("Select both hole cards for win equity.", style = MaterialTheme.typography.bodyMedium)
            }

            Text(
                text = when {
                    session.players.size != 2 || session.playersInHand != 2 -> "GTO: heads-up only; multiway shows equity and action tracking"
                    session.isCurrentStreetComplete -> "GTO: street complete — advance the street after cards are dealt"
                    session.selectedPlayerId != 0 -> "GTO: record the opponent's decision; analysis runs on Hero's turn"
                    session.potBeforeCurrentStreetBb <= 0.0 -> "GTO: record the preflop pot before postflop analysis"
                    else -> "GTO: heads-up CFR+ uses this street's exact pot, stack, and action amounts"
                },
                style = MaterialTheme.typography.labelSmall,
                color = if (
                    session.players.size == 2 &&
                    session.playersInHand == 2 &&
                    session.selectedPlayerId == 0 &&
                    !session.isCurrentStreetComplete &&
                    session.potBeforeCurrentStreetBb > 0.0
                ) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSecondaryContainer
            )
        }
    }
    if (showActionDialog) {
        ActionEntryDialog(
            playerName = session.selectedPlayer?.name ?: "Player",
            toCallBb = session.selectedPlayer?.let { (session.toCallBb - it.streetCommittedBb).coerceAtLeast(0.0) } ?: 0.0,
            onDismiss = { showActionDialog = false },
            onConfirm = { type, amount ->
                onRecordAction(type, amount)
                showActionDialog = false
            }
        )
    }
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun ActionEntryDialog(
    playerName: String,
    toCallBb: Double,
    onDismiss: () -> Unit,
    onConfirm: (PlayerActionType, Double?) -> Unit
) {
    var actionType by remember { mutableStateOf(if (toCallBb > 0.0) PlayerActionType.CALL else PlayerActionType.CHECK) }
    var amountText by remember { mutableStateOf("") }
    val needsAmount = actionType == PlayerActionType.BET || actionType == PlayerActionType.RAISE
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("${playerName}'s decision") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(if (toCallBb > 0.0) "To call: ${toCallBb.formatBb()}" else "No bet to call")
                PlayerActionType.entries.chunked(3).forEach { row ->
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                        row.forEach { type ->
                            FilterChip(
                                selected = actionType == type,
                                onClick = { actionType = type },
                                label = { Text(type.label) },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
                if (needsAmount) {
                    OutlinedTextField(
                        value = amountText,
                        onValueChange = { amountText = it },
                        label = { Text("Total commitment this street (BB)") },
                        supportingText = { Text("Enter the amount the player raises or bets to, not the increment.") },
                        singleLine = true
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    onConfirm(actionType, if (needsAmount) amountText.toDoubleOrNull() else null)
                }
            ) { Text("Record") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun PlayerCountRow(
    players: List<Int>,
    activePlayers: Int,
    onPlayersChange: (Int) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        players.forEach { playersInHand ->
            FilterChip(
                selected = activePlayers == playersInHand,
                onClick = { onPlayersChange(playersInHand) },
                label = { Text(playersInHand.toString()) },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

private val PokerRail = Color(0xFF39261A)
private val PokerFelt = Color(0xFF07563B)
private val PokerFeltInner = Color(0xFF0A6748)
private val PokerGold = Color(0xFFFFD166)
private val PokerSeat = Color(0xFF132A24)

@Composable
private fun PokerTableSurface(
    session: GameSession,
    hole: List<Card?>,
    community: List<Card?>,
    target: TargetSlot,
    onActionPlayerSelected: (Int) -> Unit,
    onSlotSelected: (TargetSlot) -> Unit,
    onClear: (TargetSlot) -> Unit,
    tableHeight: Dp? = null,
    modifier: Modifier = Modifier
) {
    val sizeModifier = if (tableHeight == null) {
        Modifier.fillMaxSize()
    } else {
        Modifier.fillMaxWidth().height(tableHeight)
    }
    Surface(
        modifier = modifier.then(sizeModifier),
        shape = RoundedCornerShape(48),
        color = PokerRail,
        shadowElevation = 8.dp
    ) {
        Surface(
            modifier = Modifier.padding(10.dp),
            shape = RoundedCornerShape(42),
            border = BorderStroke(2.dp, PokerGold.copy(alpha = 0.55f)),
            color = PokerFelt
        ) {
            Box(modifier = Modifier.fillMaxSize().padding(8.dp)) {
                Surface(
                    modifier = Modifier
                        .align(Alignment.Center)
                        .offset(y = (-34).dp)
                        .fillMaxWidth(0.76f)
                        .height(118.dp),
                    shape = RoundedCornerShape(50),
                    color = PokerFeltInner,
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.20f))
                ) {
                    Column(
                        modifier = Modifier.fillMaxSize().padding(top = 10.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Text(
                            text = "${session.street.label.uppercase()}  •  POT ${session.potBb.formatBb()}",
                            style = MaterialTheme.typography.labelMedium,
                            color = PokerGold,
                            fontWeight = FontWeight.Bold
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                            community.forEachIndexed { index, card ->
                                TableCard(
                                    card = card,
                                    label = when (index) {
                                        0 -> "F1"
                                        1 -> "F2"
                                        2 -> "F3"
                                        3 -> "T"
                                        else -> "R"
                                    },
                                    selected = target == TargetSlot.Community(index),
                                    onClick = { onSlotSelected(TargetSlot.Community(index)) },
                                    onClear = { onClear(TargetSlot.Community(index)) }
                                )
                            }
                        }
                    }
                }

                session.players.filter { it.id != 0 }.forEachIndexed { seatIndex, player ->
                    val placement = opponentSeatPlacements[seatIndex % opponentSeatPlacements.size]
                    PokerSeatChip(
                        player = player,
                        selected = session.selectedPlayerId == player.id,
                        modifier = Modifier
                            .align(placement.alignment)
                            .offset(x = placement.x, y = placement.y),
                        onClick = { onActionPlayerSelected(player.id) }
                    )
                }

                Row(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .offset(y = (-48).dp),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    hole.forEachIndexed { index, card ->
                        TableCard(
                            card = card,
                            label = "H${index + 1}",
                            selected = target == TargetSlot.Hole(index),
                            onClick = { onSlotSelected(TargetSlot.Hole(index)) },
                            onClear = { onClear(TargetSlot.Hole(index)) }
                        )
                    }
                }
                session.players.firstOrNull()?.let { hero ->
                    PokerSeatChip(
                        player = hero,
                        selected = session.selectedPlayerId == hero.id,
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .offset(y = (-8).dp),
                        onClick = { onActionPlayerSelected(hero.id) }
                    )
                }
            }
        }
    }
}

private data class SeatPlacement(
    val alignment: Alignment,
    val x: Dp = 0.dp,
    val y: Dp = 0.dp
)

private val opponentSeatPlacements = listOf(
    SeatPlacement(Alignment.TopCenter, y = 2.dp),
    SeatPlacement(Alignment.CenterEnd, x = (-8).dp, y = (-34).dp),
    SeatPlacement(Alignment.CenterStart, x = 8.dp, y = (-34).dp),
    SeatPlacement(Alignment.TopEnd, x = (-26).dp, y = 12.dp),
    SeatPlacement(Alignment.TopStart, x = 26.dp, y = 12.dp),
    SeatPlacement(Alignment.CenterEnd, x = (-8).dp, y = 36.dp),
    SeatPlacement(Alignment.CenterStart, x = 8.dp, y = 36.dp),
    SeatPlacement(Alignment.TopCenter, y = 48.dp)
)

@Composable
private fun PokerSeatChip(
    player: com.txhmhelper.model.TablePlayer,
    selected: Boolean,
    modifier: Modifier,
    onClick: () -> Unit
) {
    val borderColor = when {
        selected -> PokerGold
        !player.isInHand -> Color(0xFF8A8A8A)
        else -> Color.White.copy(alpha = 0.42f)
    }
    Surface(
        modifier = modifier
            .width(112.dp)
            .clickable(enabled = player.isInHand, onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = if (player.isInHand) PokerSeat else PokerSeat.copy(alpha = 0.45f),
        border = BorderStroke(if (selected) 2.dp else 1.dp, borderColor),
        shadowElevation = if (selected) 6.dp else 2.dp
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = player.name,
                color = Color.White,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = if (player.isInHand) {
                    "${player.stackBb.formatBb()}  •  ${player.streetCommittedBb.formatBb()} in"
                } else {
                    "folded"
                },
                color = if (selected) PokerGold else Color.White.copy(alpha = 0.78f),
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun TableCard(
    card: Card?,
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    onClear: () -> Unit
) {
    val suitColor = when (card?.suit) {
        Suit.HEARTS, Suit.DIAMONDS -> Color(0xFFB3261E)
        else -> Color(0xFF17212B)
    }
    Surface(
        modifier = Modifier
            .width(42.dp)
            .height(62.dp)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(6.dp),
        color = Color(0xFFFFFCF6),
        border = BorderStroke(if (selected) 3.dp else 1.dp, if (selected) PokerGold else Color(0xFFDDD2BF)),
        shadowElevation = 3.dp
    ) {
        Box(modifier = Modifier.fillMaxSize().padding(4.dp)) {
            Text(
                text = card?.rank?.label ?: label,
                color = suitColor,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.align(Alignment.TopStart)
            )
            Text(
                text = card?.let { suitSymbol(it.suit) } ?: "•",
                color = suitColor,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.align(Alignment.Center)
            )
            if (card != null) {
                Text(
                    text = "×",
                    color = Color(0xFF7C5C40),
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .clickable(onClick = onClear)
                )
            }
        }
    }
}

@Composable
private fun CardBoard(
    hole: List<Card?>,
    community: List<Card?>,
    target: TargetSlot,
    onSlotSelected: (TargetSlot) -> Unit,
    onClear: (TargetSlot) -> Unit,
    cardHeight: Dp = 90.dp
) {
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
private fun DialCardPicker(
    pendingSuit: Suit?,
    pendingRank: Rank?,
    usedCards: Set<Card>,
    onSuitSelected: (Suit) -> Unit,
    onRankSelected: (Rank) -> Unit,
    onResetPicker: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        color = Color(0xEE182A25),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.32f)),
        shadowElevation = 10.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            RankDial(
                selectedRank = pendingRank,
                selectedSuit = pendingSuit,
                usedCards = usedCards,
                onRankSelected = onRankSelected,
                modifier = Modifier.weight(1f)
            )
            SuitSlider(
                selectedSuit = pendingSuit,
                onSuitSelected = onSuitSelected,
                modifier = Modifier.weight(1.2f)
            )
            Text(
                text = "Reset",
                color = Color.White.copy(alpha = if (pendingSuit != null || pendingRank != null) 1f else 0.45f),
                style = MaterialTheme.typography.labelMedium,
                modifier = Modifier
                    .clickable(enabled = pendingSuit != null || pendingRank != null, onClick = onResetPicker)
                    .padding(6.dp)
            )
        }
    }
}

@Composable
private fun RankDial(
    selectedRank: Rank?,
    selectedSuit: Suit?,
    usedCards: Set<Card>,
    onRankSelected: (Rank) -> Unit,
    modifier: Modifier = Modifier
) {
    val ranks = Rank.entries
    val currentIndex = ranks.indexOf(selectedRank ?: Rank.A).coerceAtLeast(0)
    val previous = ranks[(currentIndex - 1 + ranks.size) % ranks.size]
    val current = ranks[currentIndex]
    val next = ranks[(currentIndex + 1) % ranks.size]
    fun select(rank: Rank) {
        val unavailable = selectedSuit?.let { suit -> usedCards.any { it.rank == rank && it.suit == suit } } == true
        if (!unavailable) onRankSelected(rank)
    }
    Surface(
        modifier = modifier.pointerInput(selectedRank, selectedSuit, usedCards) {
            var dragged = 0f
            detectDragGestures(
                onDragStart = { dragged = 0f },
                onDrag = { _, amount ->
                    dragged += amount.y
                    if (abs(dragged) >= 22f) {
                        val direction = if (dragged < 0f) 1 else -1
                        val rank = ranks[(currentIndex + direction + ranks.size) % ranks.size]
                        select(rank)
                        dragged = 0f
                    }
                }
            )
        },
        shape = RoundedCornerShape(18.dp),
        color = Color(0xFF233A33),
        border = BorderStroke(1.dp, PokerGold.copy(alpha = 0.72f))
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("RANK • SWIPE", color = PokerGold, style = MaterialTheme.typography.labelSmall)
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(previous.label, color = Color.White.copy(alpha = 0.45f), style = MaterialTheme.typography.labelMedium)
                Text(
                    current.label,
                    color = Color.White,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
                Text(next.label, color = Color.White.copy(alpha = 0.45f), style = MaterialTheme.typography.labelMedium)
            }
        }
    }
}

@Composable
private fun SuitSlider(
    selectedSuit: Suit?,
    onSuitSelected: (Suit) -> Unit,
    modifier: Modifier = Modifier
) {
    val suits = Suit.entries
    val selectedIndex = (selectedSuit ?: Suit.SPADES).ordinal
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text("SUIT", color = PokerGold, style = MaterialTheme.typography.labelSmall)
        Slider(
            value = selectedIndex.toFloat(),
            onValueChange = { onSuitSelected(suits[it.toInt().coerceIn(0, suits.lastIndex)]) },
            valueRange = 0f..suits.lastIndex.toFloat(),
            steps = 2,
            colors = SliderDefaults.colors(
                thumbColor = PokerGold,
                activeTrackColor = PokerGold,
                inactiveTrackColor = Color.White.copy(alpha = 0.28f)
            )
        )
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            suits.forEach { suit ->
                Text(
                    text = suitSymbol(suit),
                    color = if (suit == selectedSuit) PokerGold else Color.White.copy(alpha = 0.65f),
                    style = MaterialTheme.typography.titleSmall
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
    usedCards: Set<Card>,
    compact: Boolean = false,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = if (compact) 8.dp else 16.dp)
            .background(MaterialTheme.colorScheme.surfaceVariant),
        verticalArrangement = Arrangement.spacedBy(if (compact) 4.dp else 8.dp)
    ) {
        if (!compact) {
            Text("Tap suit then rank", style = MaterialTheme.typography.titleMedium)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(if (compact) 4.dp else 8.dp)) {
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
                Text(if (compact) "Reset" else "Reset picker")
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
