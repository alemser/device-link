package com.alemser.amplink.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Album
import androidx.compose.material.icons.outlined.Eject
import androidx.compose.material.icons.outlined.FastForward
import androidx.compose.material.icons.outlined.FastRewind
import androidx.compose.material.icons.outlined.Pause
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.PowerSettingsNew
import androidx.compose.material.icons.outlined.Radio
import androidx.compose.material.icons.outlined.Repeat
import androidx.compose.material.icons.outlined.Shuffle
import androidx.compose.material.icons.outlined.SkipNext
import androidx.compose.material.icons.outlined.SkipPrevious
import androidx.compose.material.icons.outlined.SpeakerGroup
import androidx.compose.material.icons.outlined.Stop
import androidx.compose.material.icons.outlined.DevicesOther
import androidx.compose.ui.graphics.vector.ImageVector
import com.alemser.amplink.core.KeyRef

/**
 * The words and icons for the common key names (the groove-rig vocabulary, docs/contract-v2.md "Controls"). A key
 * this list doesn't know is shown by its name with `_` as spaces, so a new device needs no change here.
 */
private val KEYS: Map<String, Pair<String, ImageVector?>> = mapOf(
    "play" to ("Play" to Icons.Outlined.PlayArrow),
    "pause" to ("Pause" to Icons.Outlined.Pause),
    "stop" to ("Stop" to Icons.Outlined.Stop),
    "previous" to ("Previous" to Icons.Outlined.SkipPrevious),
    "next" to ("Next" to Icons.Outlined.SkipNext),
    "rewind" to ("Rewind" to Icons.Outlined.FastRewind),
    "fast_forward" to ("Fast forward" to Icons.Outlined.FastForward),
    "eject" to ("Open/close" to Icons.Outlined.Eject),
    "power_toggle" to ("Power" to Icons.Outlined.PowerSettingsNew),
    "repeat" to ("Repeat" to Icons.Outlined.Repeat),
    "shuffle" to ("Random" to Icons.Outlined.Shuffle),
    "repeat_a_b" to ("A-B" to null),
    "cd_usb" to ("CD/USB" to null),
    "pure_direct" to ("Pure Direct" to null),
    "folder_up" to ("Folder +" to null),
    "folder_down" to ("Folder −" to null),
    "enter" to ("Enter" to null),
    "clear" to ("Clear" to null),
    "display" to ("Display" to null),
    "dimmer" to ("Dimmer" to null),
    "program" to ("Program" to null),
)

fun keyLabel(key: KeyRef): String =
    key.label ?: KEYS[key.key]?.first ?: key.key.removePrefix("digit_").replace('_', ' ').replaceFirstChar { it.uppercase() }

fun keyIcon(key: KeyRef): ImageVector? = KEYS[key.key]?.second

/** The icon for a kind of device in the list. */
fun kindIcon(kind: String): ImageVector = when (kind) {
    "cd_player" -> Icons.Outlined.Album
    "amplifier" -> Icons.Outlined.SpeakerGroup
    "tuner" -> Icons.Outlined.Radio
    else -> Icons.Outlined.DevicesOther
}

/** The word for a kind, under the device's name. */
fun kindLabel(kind: String): String = when (kind) {
    "cd_player" -> "CD player"
    "amplifier" -> "Amplifier"
    "tape_deck" -> "Cassette deck"
    "" -> "Device"
    else -> kind.replace('_', ' ').replaceFirstChar { it.uppercase() }
}

/** The words for common state values. */
fun stateWord(value: String): String = when (value) {
    "playing" -> "Playing"
    "paused" -> "Paused"
    "stopped" -> "Stopped"
    "loading" -> "Loading the disc"
    "open" -> "Tray open"
    "on" -> "On"
    "standby" -> "Standby"
    else -> value.replace('_', ' ').replaceFirstChar { it.uppercase() }
}
