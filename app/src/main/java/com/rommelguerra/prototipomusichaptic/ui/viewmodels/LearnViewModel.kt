package com.rommelguerra.prototipomusichaptic.ui.viewmodels

import android.app.Application
import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import com.rommelguerra.prototipomusichaptic.data.BaseDatosHelper
import com.rommelguerra.prototipomusichaptic.models.AppGlobals
import com.rommelguerra.prototipomusichaptic.models.NoteModel
import com.rommelguerra.prototipomusichaptic.services.HapticService

class LearnViewModel(application: Application) : AndroidViewModel(application) {
    private val dbHelper = BaseDatosHelper(application)
    private val hapticService = HapticService(application)
    
    var currentNote by mutableStateOf<NoteModel?>(null)
    var challengeOptions by mutableStateOf<List<NoteModel>>(emptyList())
    var selectedNoteName by mutableStateOf<String?>(null)
    var feedbackMessage by mutableStateOf("¡Escucha la nota y adivina!")
    var isSuccess by mutableStateOf<Boolean?>(null)
    var showResult by mutableStateOf(false)
    
    val correctCount get() = AppGlobals.respuestasCorrectas
    val incorrectCount get() = AppGlobals.respuestasIncorrectas
    val streak get() = AppGlobals.rachaActual

    init {
        generateNewChallenge()
    }

    fun generateNewChallenge() {
        val allNotes = dbHelper.obtenerNotasMuestrario()
        if (allNotes.isNotEmpty()) {
            val target = allNotes.random()
            currentNote = target
            
            // Generar 4 opciones aleatorias incluyendo la correcta
            val others = allNotes.filter { it.nombre != target.nombre }.shuffled()
            val options = (others.take(3) + target).shuffled()
            
            challengeOptions = options
            selectedNoteName = null
            isSuccess = null
            showResult = false
            feedbackMessage = "¡Escucha la nota y adivina!"
        }
    }

    fun playChallenge() {
        try {
            currentNote?.let { hapticService.emitirTacton(it) }
        } catch (e: SecurityException) {
            feedbackMessage = "Error de permisos BLE"
        }
    }

    fun selectNote(name: String) {
        if (!showResult) {
            selectedNoteName = name
        }
    }

    fun checkAnswer() {
        val selected = selectedNoteName ?: return
        val sharedPreferences = getApplication<Application>().getSharedPreferences("SesionUsuario", Context.MODE_PRIVATE)
        val email = sharedPreferences.getString("correoUsuario", "") ?: ""
        
        if (email.isEmpty()) return
        val idUser = dbHelper.obtenerIdUsuario(email)

        if (currentNote?.nombre == selected) {
            AppGlobals.registrarAcierto()
            isSuccess = true
            feedbackMessage = "¡Excelente! Nota correcta."
            showResult = true
            // Persistir en base de datos
            dbHelper.guardarProgreso(idUser, 1, 0, AppGlobals.rachaActual)
        } else {
            AppGlobals.registrarError()
            isSuccess = false
            feedbackMessage = "¡Ups! Nota equivocada, vuelve a intentar."
            // Persistir en base de datos
            dbHelper.guardarProgreso(idUser, 0, 1, 0)
        }
    }
}
