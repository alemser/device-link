package com.alemser.amplink.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
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
        Volume(state, device.volumeDb)
        Tile("Input", state?.inputName ?: "—", state?.input?.takeIf { it != state.inputName })
        if (device.has("tone")) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Tone("Bass", state?.bassDb, device.toneDb, Modifier.weight(1f))
                Tone("Treble", state?.trebleDb, device.toneDb, Modifier.weight(1f))
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            if (device.has("balance")) Tile("Balance", balanceText(state?.balance), modifier = Modifier.weight(1f))
            if (device.has("loudness")) Tile("Loudness", onOff(state?.loudness), modifier = Modifier.weight(1f))
            if (device.has("speakers")) Tile("Speakers", onOff(state?.speakers), modifier = Modifier.weight(1f))
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
private fun Volume(state: AmpState?, scale: Scale?) {
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
private fun Tone(label: String, value: Double?, scale: Scale?, modifier: Modifier) {
    Card(modifier) {
        Hint(label)
        Text(decibels(value, signed = true), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        if (scale != null && value != null) CentreBar(value, scale)
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
