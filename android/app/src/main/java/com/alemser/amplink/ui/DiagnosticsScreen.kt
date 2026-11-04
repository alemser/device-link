package com.alemser.amplink.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import com.alemser.amplink.core.BridgeClient
import com.alemser.amplink.core.BusStats
import com.alemser.amplink.core.Device
import com.alemser.amplink.core.duration
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.IOException

/** The contract's limit for repeating `/bus.json`. */
private const val REFRESH_MS = 2_000L

/** Near this, the longest pause is the 10 s lwIP freeze (issue #2 of sp103-display-proxy). */
private const val FREEZE_MS = 9_000L

@Composable
fun DiagnosticsScreen(client: BridgeClient, device: Device, modifier: Modifier = Modifier) {
    var stats by remember(client) { mutableStateOf<BusStats?>(null) }
    var error by remember(client) { mutableStateOf<String?>(null) }
    var confirming by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val lifecycle = LocalLifecycleOwner.current.lifecycle

    LaunchedEffect(client, lifecycle) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                try {
                    stats = client.bus()
                    error = null
                } catch (e: IOException) {
                    error = e.message ?: "Couldn't reach the bridge"
                }
                delay(REFRESH_MS)
            }
        }
    }

    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        stats?.let { s ->
            Section("Display bus") {
                val froze = s.maxGapMs >= FREEZE_MS
                Stat("Longest pause", "${s.maxGapMs} ms", if (froze) Warning else null)
                if (froze) Hint("The bridge froze: a dead connection may have held its network memory")
                Stat("Largest batch", "${s.maxBatch} words", if (s.maybeLost) Warning else null)
                if (s.maybeLost) Hint("Some words may have been lost")
                Stat("Screens read", s.screens.toString())
                Stat("Unknown screens", s.unknownScreens.toString(), if (s.unknownScreens > 0) Warning else null)
                Stat("Last screen", s.lastScreenS?.let { duration(it) + " ago" } ?: "—")
                Stat("Amp power-ons", s.powerOns.toString())
                Stat("Writes / reads", "${s.writes} / ${s.reads}")
            }
            Section("Log") {
                Stat("Kept", "${s.logWords} of ${s.logSize} words")
                Stat("Covers", duration(s.logSpanS))
                Stat("Counting for", duration(s.sinceS))
                Stat("Bridge clock", s.clock?.take(CLOCK_CHARS) ?: "Not set")
                OutlinedButton(onClick = { confirming = true }, modifier = Modifier.fillMaxWidth()) {
                    Text("Clear log and statistics")
                }
            }
        }
        Section("Bridge") {
            Stat("Model", device.model)
            Stat("Version", device.bridgeVersion ?: "—")
            Stat("Address", client.host)
        }
    }

    if (confirming) {
        AlertDialog(
            onDismissRequest = { confirming = false },
            title = { Text("Clear the log?") },
            text = { Text("The words and the statistics kept on the bridge are erased.") },
            confirmButton = {
                TextButton(onClick = {
                    confirming = false
                    scope.launch {
                        try {
                            client.clearBus()
                        } catch (e: IOException) {
                            error = e.message ?: "Couldn't reach the bridge"
                        }
                    }
                }) { Text("Clear") }
            },
            dismissButton = { TextButton(onClick = { confirming = false }) { Text("Cancel") } },
        )
    }
}

/** "2026-11-04 14:21:35", without the milliseconds. */
private const val CLOCK_CHARS = 19

@Composable
private fun Stat(label: String, value: String, color: Color? = null) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, color = color ?: MaterialTheme.colorScheme.onSurface)
    }
}
