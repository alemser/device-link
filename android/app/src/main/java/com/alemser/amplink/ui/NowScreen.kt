package com.alemser.amplink.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alemser.amplink.core.AmpState
import com.alemser.amplink.core.BridgeClient
import com.alemser.amplink.core.Device
import com.alemser.amplink.core.Link
import com.alemser.amplink.core.Scale
import com.alemser.amplink.core.balanceText
import com.alemser.amplink.core.decibels

/**
 * The only screen that keeps `/events` open. `collectAsStateWithLifecycle` closes it when the app
 * leaves the screen, and when another tab replaces this one.
 */
@Composable
fun NowScreen(client: BridgeClient, device: Device, modifier: Modifier = Modifier) {
    val stream = remember(client) { client.live() }
    val link by stream.collectAsStateWithLifecycle(Link.Connecting)
    val state = (link as? Link.Live)?.state
    val columns = device.display?.columns ?: DEFAULT_COLUMNS
    val scope = rememberCoroutineScope()
    val commands = remember(scope) { Commands(scope) }
    val control = device.has("control")
    val on = control && state?.power == "on"
    val step: (String, Boolean) -> Unit = { target, up -> commands.run { client.step(target, up) } }
    val switch: (String, Boolean) -> Unit = { target, value -> commands.run { client.switch(target, value) } }

    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (device.display != null) {
            Lcd(state?.lcd?.takeIf { it.isNotEmpty() } ?: List(device.display.rows) { "" }, columns, dim = state == null)
        }
        Hint(linkText(link, state))
        commands.error?.let { Hint(it, MaterialTheme.colorScheme.error) }
        if (control && state?.power != null) {
            OutlinedButton(
                onClick = { commands.run { client.key("power_toggle") } },
                enabled = !commands.working,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (state.power == "on") "Standby" else "Turn on") }
        }
        Volume(state, device.volumeDb, on, commands.working) { up -> step("volume", up) }
        Tile("Input", state?.inputName ?: "—", state?.input?.takeIf { it != state.inputName })
        if (on) {
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                device.inputs.forEach { input ->
                    FilterChip(
                        selected = input.id == state?.inputId,
                        onClick = { commands.run { client.key("select_${input.id}") } },
                        label = { Text(input.name) },
                        enabled = !commands.working,
                    )
                }
            }
        }
        if (device.has("tone")) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Tone("Bass", state?.bassDb, device.toneDb, on, commands.working, Modifier.weight(1f)) { step("bass", it) }
                Tone("Treble", state?.trebleDb, device.toneDb, on, commands.working, Modifier.weight(1f)) { step("treble", it) }
            }
        }
        if (device.has("balance")) {
            Card(Modifier.fillMaxWidth()) {
                Hint("Balance")
                Text(balanceText(state?.balance), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                if (on) PlusMinus(commands.working) { step("balance", it) }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            if (device.has("loudness")) {
                Toggle("Loudness", state?.loudness, on, commands.working, Modifier.weight(1f)) { switch("loudness", it) }
            }
            if (device.has("speakers")) {
                Toggle("Speakers", state?.speakers, on, commands.working, Modifier.weight(1f)) { switch("speakers", it) }
            }
        }
    }
}

private const val DEFAULT_COLUMNS = 16

private fun linkText(link: Link, state: AmpState?): String = when (link) {
    Link.Connecting -> "Connecting…"
    is Link.Lost -> "Disconnected, retrying…"
    is Link.Live -> when (state?.power) {
        "on" -> "On"
        "standby" -> "Standby"
        else -> "Connected. The amp hasn't shown its state yet"
    }
}

private fun onOff(value: Boolean?) = when (value) {
    true -> "On"
    false -> "Off"
    null -> "—"
}

@Composable
private fun Card(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Surface(shape = RoundedCornerShape(14.dp), color = MaterialTheme.colorScheme.surfaceContainer, modifier = modifier) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) { content() }
    }
}

@Composable
private fun Volume(state: AmpState?, scale: Scale?, canChange: Boolean, working: Boolean, onStep: (Boolean) -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Hint("Volume")
        Text(
            decibels(state?.volumeDb),
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.SemiBold,
        )
        val value = state?.volumeDb
        if (scale != null && value != null) {
            LinearProgressIndicator(
                progress = { ((value - scale.min) / (scale.max - scale.min)).toFloat().coerceIn(0f, 1f) },
                modifier = Modifier.fillMaxWidth(),
                drawStopIndicator = {},
            )
        }
        if (canChange) PlusMinus(working, onStep)
    }
}

@Composable
private fun PlusMinus(working: Boolean, onStep: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        FilledTonalButton(onClick = { onStep(false) }, enabled = !working, modifier = Modifier.weight(1f)) { Text("−") }
        FilledTonalButton(onClick = { onStep(true) }, enabled = !working, modifier = Modifier.weight(1f)) { Text("+") }
    }
}

/** `null` is "not known": it shows as a dash, and the switch appears off until the amp tells. */
@Composable
private fun Toggle(label: String, value: Boolean?, canChange: Boolean, working: Boolean, modifier: Modifier, onChange: (Boolean) -> Unit) {
    Card(modifier) {
        Hint(label)
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            Text(onOff(value), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            if (canChange) Switch(checked = value == true, onCheckedChange = onChange, enabled = !working)
        }
    }
}

@Composable
private fun Tile(label: String, value: String, note: String? = null, modifier: Modifier = Modifier.fillMaxWidth()) {
    Card(modifier) {
        Hint(label)
        Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        note?.let { Hint(it) }
    }
}

@Composable
private fun Tone(label: String, value: Double?, scale: Scale?, canChange: Boolean, working: Boolean, modifier: Modifier, onStep: (Boolean) -> Unit) {
    Card(modifier) {
        Hint(label)
        Text(decibels(value, signed = true), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        if (scale != null && value != null) CentreBar(value, scale)
        if (canChange) PlusMinus(working, onStep)
    }
}

/** A bar that grows from the middle: tone is a cut or a boost, not a level. */
@Composable
private fun CentreBar(value: Double, scale: Scale) {
    val track = MaterialTheme.colorScheme.surfaceVariant
    val fill = MaterialTheme.colorScheme.primary
    Canvas(
        Modifier
            .fillMaxWidth()
            .height(6.dp),
    ) {
        drawRect(track)
        val half = size.width / 2
        val part = (value / scale.max).toFloat().coerceIn(-1f, 1f) * half
        drawRect(fill, Offset(minOf(half, half + part), 0f), Size(kotlin.math.abs(part), size.height))
    }
}
