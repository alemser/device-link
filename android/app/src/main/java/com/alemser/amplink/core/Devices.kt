package com.alemser.amplink.core

import android.content.SharedPreferences
import androidx.core.content.edit
import kotlinx.serialization.SerializationException
import kotlinx.serialization.builtins.ListSerializer

/** A device in the list: what discovery said last, and whether it answered the latest rounds. */
data class ListedDevice(val bridge: FoundBridge, val online: Boolean, val new: Boolean)

/**
 * The devices this phone has seen, keyed by their stable name (docs/contract-v2.md, Discovery), kept across runs so
 * the list shows a device switched off as offline instead of forgetting it, and marks one never seen before as new.
 */
class KnownDevices(private val prefs: SharedPreferences) {
    private val serializer = ListSerializer(FoundBridge.serializer())
    private var known: Map<String, FoundBridge> = load()
    private val missed = mutableMapOf<String, Int>()
    private val fresh = mutableSetOf<String>()

    /** Folds in one discovery round and gives the list to show: online first, then by name. */
    fun update(found: List<FoundBridge>): List<ListedDevice> {
        val now = found.associateBy { it.name }
        now.keys.filter { it !in known }.forEach { fresh += it }
        known.keys.forEach { name -> missed[name] = if (name in now) 0 else (missed[name] ?: 0) + 1 }
        now.keys.forEach { missed[it] = 0 }
        known = known + now
        save()
        return list()
    }

    /** What the list last knew about [name], if anything (an api 1 bridge's label is filled in from its /device). */
    fun get(name: String): FoundBridge? = known[name]

    fun list(): List<ListedDevice> = known.values
        .map { ListedDevice(it, (missed[it.name] ?: MISSED_OFFLINE) < MISSED_OFFLINE, it.name in fresh) }
        .sortedWith(compareBy({ !it.online }, { it.bridge.title }))

    /** Opening a device clears its "new" mark. */
    fun seen(name: String) {
        fresh -= name
    }

    fun forget(name: String) {
        known = known - name
        fresh -= name
        save()
    }

    private fun load(): Map<String, FoundBridge> = try {
        prefs.getString(KEY, null)?.let { Wire.decodeFromString(serializer, it) }.orEmpty().associateBy { it.name }
    } catch (_: SerializationException) {
        emptyMap()
    } catch (_: IllegalArgumentException) {
        emptyMap()
    }

    private fun save() = prefs.edit { putString(KEY, Wire.encodeToString(serializer, known.values.toList())) }

    private companion object {
        const val KEY = "devices"

        /** Chosen: discovery runs every 5 s, and a probe is sometimes lost; 3 missed rounds is 15 s of silence. */
        const val MISSED_OFFLINE = 3
    }
}
