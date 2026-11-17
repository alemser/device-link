package com.alemser.amplink.core

fun isIpv4(text: String): Boolean {
    val parts = text.split(".")
    return parts.size == 4 && parts.all { part ->
        part.isNotEmpty() && part.all(Char::isDigit) && (part.toIntOrNull() ?: 256) < 256
    }
}
