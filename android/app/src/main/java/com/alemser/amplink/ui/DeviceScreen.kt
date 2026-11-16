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
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
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
import com.alemser.amplink.core.ControlGroup
import com.alemser.amplink.core.Description
import com.alemser.amplink.core.Feed
import com.alemser.amplink.core.Release
import com.alemser.amplink.core.SettingField
import com.alemser.amplink.core.StateField
import com.alemser.amplink.core.UpdateStep
import com.alemser.amplink.core.Updater
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull
import java.io.IOException

/**
 * An api 2 device's screen, built from its description (docs/contract-v2.md): the state fields, the remote by group,
 * the settings, and the firmware. The only place that keeps this device's `/events` open.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceScreen(client: BridgeClient, title: String, onBack: () -> Unit) {
    BackHandler(onBack = onBack)
    var description by remember(client) { mutableStateOf<Description?>(null) }
    var error by remember(client) { mutableStateOf<String?>(null) }
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
}

@Composable
private fun DeviceBody(client: BridgeClient, description: Description, modifier: Modifier) {
    val stream = remember(client) { client.feed() }
    val feed by stream.collectAsStateWithLifecycle(Feed.Connecting)
    val state = (feed as? Feed.Live)?.state
    val scope = rememberCoroutineScope()
    val commands = remember(scope) { Commands(scope) }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(16.dp)) {
        StatusSection(description.state, state, feed)
        commands.error?.let { Hint(it, MaterialTheme.colorScheme.error) }
        description.controls.forEach { group -> ControlSection(group, state, commands, client) }
        if (description.settings.isNotEmpty()) SettingsSection(client, description.settings)
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
            if (!lines.isNullOrEmpty()) Lcd(lines, lines.maxOf { it.length }.coerceAtLeast(1), dim = state == null)
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

/** The value at a dotted path ("media.track"), or null. */
private fun at(state: JsonObject?, path: String): JsonElement? {
    var node: JsonElement? = state
    for (part in path.split('.')) node = (node as? JsonObject)?.get(part)
    return node.takeIf { it != JsonNull }
}

/** A state value as text, by its field's type; null when unknown (not shown, never as zero or off). */
private fun show(field: StateField, value: JsonElement?): String? {
    val p = value as? JsonPrimitive ?: return null
    return when (field.type) {
        "enum" -> p.contentOrNull?.let(::stateWord)
        "duration" -> p.longOrNull?.let { "%d:%02d".format(it / 60, it % 60) }
        "bool" -> p.booleanOrNull?.let { if (it) "On" else "Off" }
        "int", "number" -> p.contentOrNull?.let { if (field.unit != null) "$it ${field.unit}" else it }
        else -> p.contentOrNull
    }
}

// ---------------------------------------------------------------- remote

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ControlSection(group: ControlGroup, state: JsonObject?, commands: Commands, client: BridgeClient) {
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
            val value = bound.state?.let { at(state, it) as? JsonPrimitive }?.contentOrNull ?: "—"
            Stepper(bound.label ?: groupTitle(bound.target), value, !commands.working, !commands.working,
                onDown = { commands.run { client.step(bound.target, false) } },
                onUp = { commands.run { client.step(bound.target, true) } })
        }
        group.switches.forEach { bound ->
            val on = bound.state?.let { at(state, it) as? JsonPrimitive }?.booleanOrNull ?: false
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
    else -> group.replace('_', ' ').replaceFirstChar { it.uppercase() }
}

// ---------------------------------------------------------------- settings

/** Edits wait 1 s after the last change before the PATCH: each write goes to the device's flash. */
@Composable
private fun SettingsSection(client: BridgeClient, fields: List<SettingField>) {
    var values by remember(client) { mutableStateOf<JsonObject?>(null) }
    var pending by remember(client) { mutableStateOf<Map<String, JsonElement>>(emptyMap()) }
    var error by remember(client) { mutableStateOf<String?>(null) }
    LaunchedEffect(client) {
        values = runCatching { client.settings() }.onFailure { error = it.message }.getOrNull()
    }
    LaunchedEffect(pending) {
        if (pending.isEmpty()) return@LaunchedEffect
        delay(1_000)
        try {
            values = client.patchSettings(JsonObject(pending))
            pending = emptyMap()
            error = null
        } catch (e: IOException) {
            error = e.message
        }
    }
    fields.groupBy { it.group ?: "Settings" }.forEach { (title, group) ->
        Section(title) {
            group.forEach { field ->
                val current = pending[field.id] ?: values?.get(field.id)
                val text = (current as? JsonPrimitive)?.contentOrNull.orEmpty()
                when (field.type) {
                    "bool" -> SwitchRow(field.label ?: field.id, (current as? JsonPrimitive)?.booleanOrNull ?: false) {
                        pending = pending + (field.id to JsonPrimitive(it))
                    }
                    "enum" -> FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        field.values.forEach { v ->
                            FilterChip(selected = v == text, onClick = { pending = pending + (field.id to JsonPrimitive(v)) },
                                label = { Text(stateWord(v)) })
                        }
                    }
                    else -> OutlinedTextField(
                        value = text,
                        onValueChange = { typed ->
                            val clipped = field.max?.let { typed.take(it.toInt()) } ?: typed
                            pending = pending + (field.id to JsonPrimitive(clipped))
                        },
                        label = { Text(field.label ?: field.id) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
            error?.let { Hint(it, MaterialTheme.colorScheme.error) }
        }
    }
}

// ---------------------------------------------------------------- firmware

@Composable
private fun FirmwareSection(client: BridgeClient, repo: String, running: String?) {
    val updater = remember { Updater() }
    val scope = rememberCoroutineScope()
    var latest by remember(client) { mutableStateOf<Pair<Release, Map<String, String>>?>(null) }
    var step by remember(client) { mutableStateOf<UpdateStep?>(null) }
    var error by remember(client) { mutableStateOf<String?>(null) }
    var busy by remember(client) { mutableStateOf(false) }
    LaunchedEffect(repo) { latest = runCatching { updater.latest(repo) }.getOrNull() }

    Section("Firmware") {
        Text("Version ${running ?: "?"}")
        val release = latest?.first
        when {
            release == null -> Hint("No release found for $repo")
            release.version == running && step == null -> Hint("Up to date")
            else -> {
                if (step == null) Hint("Version ${release.version} is available")
                Button(
                    onClick = {
                        busy = true
                        error = null
                        scope.launch {
                            try {
                                updater.install(client, release, latest!!.second) { step = it }
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
