package com.alemser.amplink.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alemser.amplink.core.BridgeClient
import com.alemser.amplink.core.Check
import com.alemser.amplink.core.ControlGroup
import com.alemser.amplink.core.Description
import com.alemser.amplink.core.Feed
import com.alemser.amplink.core.NoRelease
import com.alemser.amplink.core.Offer
import com.alemser.amplink.core.StateField
import com.alemser.amplink.core.UpdateStep
import com.alemser.amplink.core.WifiSetupClient
import com.alemser.amplink.core.Updater
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull
import java.io.IOException

/**
 * An api 2 device's screen, built from its description (docs/contract-v2.md): the state fields, the remote by group,
 * and the firmware. The only place that keeps this device's `/events` open.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceScreen(client: BridgeClient, title: String, onBack: () -> Unit, onSetup: () -> Unit) {
    BackHandler(onBack = onBack)
    var description by remember(client) { mutableStateOf<Description?>(null) }
    var error by remember(client) { mutableStateOf<String?>(null) }
    var wifiDialog by remember(client) { mutableStateOf(false) }
    LaunchedEffect(client) {
        try {
            description = client.description()
        } catch (e: IOException) {
            error = e.message ?: "The device didn't answer"
        }
    }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(description?.model ?: title, maxLines = 1) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "Devices") }
                },
                actions = {
                    if (description?.has("wifi_setup") == true) {
                        IconButton(onClick = { wifiDialog = true }) { Icon(Icons.Outlined.Wifi, contentDescription = "Wi-Fi") }
                    }
                },
            )
        },
    ) { padding ->
        val page = Modifier
            .padding(padding)
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
        val found = description
        when {
            found != null -> DeviceBody(client, found, page)
            error != null -> Column(page) { Text("Couldn't open the device: $error", color = MaterialTheme.colorScheme.error) }
            else -> Column(page, horizontalAlignment = Alignment.CenterHorizontally) { CircularProgressIndicator() }
        }
    }
    if (wifiDialog) WifiDialog(client.host, onClose = { wifiDialog = false }, onSetup = onSetup)
}

/** Moving a device to another Wi-Fi: it opens its setup network for 10 minutes, without leaving this one. */
@Composable
private fun WifiDialog(host: String, onClose: () -> Unit, onSetup: () -> Unit) {
    val scope = rememberCoroutineScope()
    var error by remember { mutableStateOf<String?>(null) }
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Wi-Fi") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Hint("At $host")
                TextButton(onClick = {
                    scope.launch {
                        try {
                            WifiSetupClient(host).openSetup()
                            onClose()
                            onSetup()
                        } catch (e: IOException) {
                            error = e.message ?: "The device didn't answer"
                        }
                    }
                }) { Text("Change this device's Wi-Fi") }
                error?.let { Hint(it, MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text("Close") } },
    )
}

@Composable
private fun DeviceBody(client: BridgeClient, description: Description, modifier: Modifier) {
    val stream = remember(client) { client.feed() }
    val feed by stream.collectAsStateWithLifecycle(Feed.Connecting)
    val state = (feed as? Feed.Live)?.state
    val scope = rememberCoroutineScope()
    val commands = remember(scope) { Commands(scope) }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(16.dp)) {
        // A field a control already shows (volume next to its − and +) is not repeated in the status.
        val bound = description.controls.flatMap { g -> (g.steps + g.switches).mapNotNull { it.state } + listOfNotNull(g.select?.state) }
        StatusSection(description.state.filter { it.id !in bound }, state, feed)
        commands.error?.let { Hint(it, MaterialTheme.colorScheme.error) }
        val units = description.state.associate { it.id to it.unit }
        description.controls.forEach { group -> ControlSection(group, state, commands, client, units) }
        if (description.has("update") && description.firmware != null) {
            FirmwareSection(client, description.firmware, description.bridgeVersion)
        }
    }
}

// ---------------------------------------------------------------- state

@Composable
private fun StatusSection(fields: List<StateField>, state: JsonObject?, feed: Feed) {
    Section("Now") {
        fields.filter { it.type == "lines" }.forEach { field ->
            val lines = (at(state, field.id) as? kotlinx.serialization.json.JsonArray)?.map { it.jsonPrimitive.content }
            // The device says its width; blank lines (an amp in standby) must not make one huge column.
            if (!lines.isNullOrEmpty()) {
                val columns = field.columns ?: maxOf(lines.maxOf { it.length }, DEFAULT_COLUMNS)
                Lcd(lines, columns, dim = state == null)
            }
        }
        fields.filter { it.type != "lines" }.forEach { field ->
            val value = show(field, at(state, field.id)) ?: return@forEach
            if (field.type == "enum" && field.label == null) {
                Text(value, style = MaterialTheme.typography.headlineSmall)
            } else {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(field.label ?: field.id)
                    Text(value, style = MaterialTheme.typography.titleMedium)
                }
            }
        }
        when (feed) {
            Feed.Connecting -> Hint("Connecting…")
            is Feed.Lost -> Hint("Not live: ${feed.why}. Trying again…", MaterialTheme.colorScheme.error)
            is Feed.Live -> Unit
        }
    }
}

private const val DEFAULT_COLUMNS = 16

/** The value at a dotted path ("media.track"), or null. */
private fun at(state: JsonObject?, path: String): JsonElement? {
    var node: JsonElement? = state
    for (part in path.split('.')) node = (node as? JsonObject)?.get(part)
    return node.takeIf { it != JsonNull }
}

/** Seconds as "2:07", or "40 h 47 min" from an hour up. */
private fun duration(s: Long): String =
    if (s < 3600) "%d:%02d".format(s / 60, s % 60) else "%d h %02d min".format(s / 3600, s % 3600 / 60)

/** A state value as text, by its field's type; null when unknown (not shown, never as zero or off). */
private fun show(field: StateField, value: JsonElement?): String? {
    val p = value as? JsonPrimitive ?: return null
    return when (field.type) {
        "enum" -> p.contentOrNull?.let(::stateWord)
        "duration" -> p.longOrNull?.let(::duration)
        "bool" -> p.booleanOrNull?.let { if (it) "On" else "Off" }
        "int", "number" -> p.contentOrNull?.let { if (field.unit != null) "$it ${field.unit}" else it }
        else -> p.contentOrNull
    }
}

// ---------------------------------------------------------------- remote

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ControlSection(
    group: ControlGroup,
    state: JsonObject?,
    commands: Commands,
    client: BridgeClient,
    units: Map<String, String?>,
) {
    Section(groupTitle(group.group)) {
        if (group.keys.isNotEmpty()) {
            val iconsOnly = group.keys.all { keyIcon(it) != null }
            FlowRow(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp, if (iconsOnly) Alignment.CenterHorizontally else Alignment.Start),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                group.keys.forEach { key ->
                    val icon = keyIcon(key)
                    if (icon != null && iconsOnly) {
                        FilledTonalIconButton(
                            onClick = { commands.run { client.press(key.key) } },
                            enabled = !commands.working,
                            modifier = Modifier.size(52.dp),
                        ) { Icon(icon, contentDescription = keyLabel(key)) }
                    } else {
                        OutlinedButton(
                            onClick = { commands.run { client.press(key.key) } },
                            enabled = !commands.working,
                        ) { Text(keyLabel(key)) }
                    }
                }
            }
        }
        group.steps.forEach { bound ->
            val raw = bound.state?.let { at(state, it) as? JsonPrimitive }?.contentOrNull
            val unit = bound.state?.let { units[it] }
            val value = raw?.let { if (unit != null) "$it $unit" else it } ?: "—"
            Stepper(bound.label ?: groupTitle(bound.target), value, !commands.working, !commands.working,
                onDown = { commands.run { client.step(bound.target, false) } },
                onUp = { commands.run { client.step(bound.target, true) } })
        }
        group.switches.forEach { bound ->
            val on = bound.state?.let { at(state, it) as? JsonPrimitive }?.booleanOrNull   // null: unknown, not off
            SwitchRow(bound.label ?: groupTitle(bound.target), on) { commands.run { client.switch(bound.target, it) } }
        }
        group.select?.let { select ->
            val current = select.state?.let { at(state, it) as? JsonPrimitive }?.contentOrNull
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                select.options.forEach { option ->
                    FilterChip(
                        selected = option.id == current,
                        onClick = { commands.run { client.press(option.key) } },
                        label = { Text(option.name) },
                        enabled = !commands.working,
                    )
                }
            }
        }
    }
}

private fun groupTitle(group: String): String = when (group) {
    "transport" -> "Playback"
    "numbers" -> "Track number"
    "modes" -> "Modes"
    "source" -> "Source"
    "power" -> "Power"
    "volume" -> "Volume"
    "input" -> "Input"
    "tone" -> "Tone and balance"
    else -> group.replace('_', ' ').replaceFirstChar { it.uppercase() }
}

// ---------------------------------------------------------------- firmware

@Composable
private fun FirmwareSection(client: BridgeClient, repo: String, running: String?) {
    val updater = remember { Updater() }
    val scope = rememberCoroutineScope()
    var latest by remember(client) { mutableStateOf<Check?>(null) }
    var step by remember(client) { mutableStateOf<UpdateStep?>(null) }
    var error by remember(client) { mutableStateOf<String?>(null) }
    var busy by remember(client) { mutableStateOf(false) }
    var lookup by remember(client) { mutableStateOf<String?>("Looking for updates…") }
    LaunchedEffect(repo, running) {
        lookup = try {
            latest = updater.check(repo, running)
            null
        } catch (e: NoRelease) {
            "No release found for $repo"
        } catch (e: IOException) {
            // Offline, or GitHub's hourly limit: say so, rather than "no release".
            "Couldn't look for updates: ${e.message ?: "no answer"}"
        }
    }

    Section("Firmware") {
        Text("Version ${running ?: "?"}")
        Hint("At ${client.host}")
        val check = latest
        val release = check?.release
        when {
            check == null || release == null -> lookup?.let { Hint(it) }
            check.offer == Offer.UP_TO_DATE && step == null -> Hint("Up to date")
            // Sent from a computer: an older release would undo it (device-link#9).
            check.offer == Offer.AHEAD && step == null -> Hint("Newer than the newest release (${release.version})")
            else -> {
                if (step == null) Hint("Version ${release.version} is available")
                Button(
                    onClick = {
                        busy = true
                        error = null
                        scope.launch {
                            try {
                                updater.install(client, release, check.assets) { step = it }
                            } catch (e: IOException) {
                                error = e.message ?: "The update failed; nothing was applied"
                            } finally {
                                busy = false
                            }
                        }
                    },
                    enabled = !busy && step !is UpdateStep.Done,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Update to ${release.version}") }
            }
        }
        when (val s = step) {
            is UpdateStep.Sending -> Hint("Sending ${s.file} (${s.done + 1} of ${s.total})")
            UpdateStep.Restarting -> Hint("The device restarts and tries the new version…")
            is UpdateStep.Done -> Hint("Updated to ${s.version}")
            is UpdateStep.RolledBack -> Hint("The device went back to the previous version: ${s.why}", MaterialTheme.colorScheme.error)
            null -> Unit
        }
        error?.let { Hint(it, MaterialTheme.colorScheme.error) }
    }
}
