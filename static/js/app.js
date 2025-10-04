// Variables globales
let chatMessages = [];
let teachersList = [];

// Elementos del DOM
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const chatMessagesDiv = document.getElementById('chat-messages');
const typingIndicator = document.querySelector('.typing-indicator');
const sendBtn = document.querySelector('.send-btn');

// Verificar que los elementos existen
if (!chatForm || !messageInput || !sendBtn) {
    console.error('Error: No se encontraron elementos del DOM necesarios');
}

// Función para cargar la lista de profesores al inicializar
async function loadTeachersList() {
    try {
        const response = await fetch('/api/teachers');
        const data = await response.json();
        
        if (data.status === 'success') {
            teachersList = data.teachers;
            console.log('Llista de professors carregada:', teachersList.length, 'professors');
        } else {
            console.error('Error carregant professors:', data.error);
        }
    } catch (error) {
        console.error('Error al obtenir llista de professors:', error);
    }
}

// Manejo del input de mensajes
messageInput.addEventListener('input', () => {
    // Ajustar altura del textarea automáticamente
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
    
    // Habilitar/deshabilitar botón de envío
    if (sendBtn) {
        sendBtn.disabled = !messageInput.value.trim();
    }
});

// Manejo del envío de mensajes
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Agregar mensaje del usuario
    addMessage(message, 'user');
    
    // Limpiar input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;
    
    // Detectar intención antes de enviar al bot
    const intent = detectIntent(message);
    
    if (intent === 'absence') {
        // Mostrar formulario de justificación
        addMessage("Entenc que vols justificar una falta. Si us plau, omple aquest formulari:", 'bot');
        createAbsenceForm();
    } else if (intent === 'teacher_contact') {
        // Mostrar formulario de contacto
        addMessage("Vols contactar amb un professor. Si us plau, omple aquest formulari:", 'bot');
        createTeacherContactForm();
    } else {
        // Mostrar indicador de escritura y obtener respuesta normal
        showTypingIndicator();
        
        try {
            const response = await getBotResponse(message);
            hideTypingIndicator();
            addMessage(response, 'bot');
        } catch (error) {
            hideTypingIndicator();
            addMessage("Ho sento, hi ha hagut un error. Si us plau, torna-ho a intentar.", 'bot');
        }
    }
});

// Función para agregar mensajes al chat
function addMessage(text, sender, isForm = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = sender === 'user' ? 'user-avatar' : 'bot-avatar';
    
    if (sender === 'user') {
        const userName = userData.nom || 'U';
        avatarDiv.textContent = userName.charAt(0).toUpperCase();
    } else {
        avatarDiv.textContent = 'R';
    }
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Si es un formulario, insertarlo directamente
    if (isForm) {
        contentDiv.innerHTML = text;
    } else {
        contentDiv.innerHTML = formatMessage(text);
    }
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString('ca-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    bubbleDiv.appendChild(contentDiv);
    bubbleDiv.appendChild(timeDiv);
    
    if (sender === 'user') {
        messageDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(avatarDiv);
    } else {
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(bubbleDiv);
    }
    
    chatMessagesDiv.appendChild(messageDiv);
    
    // Scroll automático al último mensaje
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
    
    // Guardar mensaje en el historial
    chatMessages.push({
        text,
        sender,
        timestamp: new Date()
    });
}

// Función para formatear mensajes
function formatMessage(text) {
    // Convertir saltos de línea
    text = text.replace(/\n/g, '<br>');
    
    // Detectar y convertir URLs en enlaces
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    text = text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    
    // Detectar emails
    const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/g;
    text = text.replace(emailRegex, '<a href="mailto:$1">$1</a>');
    
    return text;
}

// Función para mostrar/ocultar indicador de escritura
function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// Función para obtener respuesta del bot
async function getBotResponse(message) {
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error('Error en la respuesta del servidor');
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            return data.response;
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error al obtener respuesta:', error);
        throw error;
    }
}

// Función para detectar la intención del mensaje
function detectIntent(message) {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('justificar') || lowerMessage.includes('falta') || 
        lowerMessage.includes('absència') || lowerMessage.includes('absent')) {
        return 'absence';
    } else if (lowerMessage.includes('contactar') || lowerMessage.includes('professor') || 
               lowerMessage.includes('tutor') || lowerMessage.includes('reunió') || 
               lowerMessage.includes('cita') || lowerMessage.includes('parlar amb')) {
        return 'teacher_contact';
    }
    
    return null;
}

// Permitir enviar con Enter (pero Shift+Enter para nueva línea)
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (sendBtn && !sendBtn.disabled) {
            chatForm.dispatchEvent(new Event('submit'));
        }
    }
});

// Función para crear formulario de justificación de falta
function createAbsenceForm() {
    const formId = 'absence-form-' + Date.now();
    const today = new Date().toISOString().split('T')[0];
    const formHTML = `
        <form id="${formId}" class="email-form">
            <h4>📋 Justificació de Falta d'Assistència</h4>
            <div class="form-field">
                <label>Nom de l'alumne:</label>
                <input type="text" name="alumne" required placeholder="Ex: Maria García Pérez" autocomplete="name">
            </div>
            <div class="form-field">
                <label>Curs i grup:</label>
                <input type="text" name="curs" required placeholder="Ex: 2n ESO A" list="courses">
                <datalist id="courses">
                    <option value="1r ESO A">
                    <option value="1r ESO B">
                    <option value="2n ESO B">
                    <option value="3r ESO A">
                    <option value="3r ESO B">
                    <option value="4t ESO A">
                    <option value="4t ESO B">
                    <option value="1r Batxillerat">
                    <option value="2n Batxillerat">
                </datalist>
            </div>
            <div class="form-field">
                <label>Data de l'absència:</label>
                <input type="date" name="data" required value="${today}" max="${today}">
            </div>
            <div class="form-field">
                <label>Motiu:</label>
                <textarea name="motiu" required placeholder="Ex: Visita mèdica programada" rows="3"></textarea>
            </div>
            <div class="form-actions">
                <button type="submit" class="btn-primary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                    </svg>
                    Enviar justificació
                </button>
                <button type="button" class="btn-secondary" onclick="cancelForm('${formId}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                       <line x1="6" y1="6" x2="18" y2="18"></line>
                   </svg>
                   Cancel·lar
               </button>
           </div>
       </form>
   `;
   
   addMessage(formHTML, 'bot', true);
   
   // Manejar envío del formulario
   setTimeout(() => {
       const form = document.getElementById(formId);
       if (form) {
           form.addEventListener('submit', async (e) => {
               e.preventDefault();
               const formData = new FormData(e.target);
               const data = Object.fromEntries(formData);
               
               // Construir mensaje para enviar
               const message = `Justificar falta - Alumne: ${data.alumne}, Curs: ${data.curs}, Data: ${data.data}, Motiu: ${data.motiu}`;
               
               // Deshabilitar el formulario con animación
               e.target.style.opacity = '0.5';
               e.target.querySelectorAll('input, textarea, button').forEach(el => el.disabled = true);
               
               // Añadir indicador de carga
               const submitBtn = e.target.querySelector('.btn-primary');
               submitBtn.innerHTML = '<span style="display: inline-block; animation: spin 1s linear infinite;">⏳</span> Enviant...';
               
               // Enviar al backend
               try {
                   const response = await getBotResponse(message);
                   addMessage(response, 'bot');
                   // Ocultar formulario después de enviar
                   e.target.style.display = 'none';
               } catch (error) {
                   addMessage("Ho sento, hi ha hagut un error. Si us plau, torna-ho a intentar.", 'bot');
                   // Reactivar formulario en caso de error
                   e.target.style.opacity = '1';
                   e.target.querySelectorAll('input, textarea, button').forEach(el => el.disabled = false);
                   submitBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg> Enviar justificació`;
               }
           });
       }
   }, 100);
}

// Función para crear formulario de contacto con profesor
function createTeacherContactForm() {
    const formId = 'teacher-form-' + Date.now();
    
    // Generar opciones del datalist con la lista cargada
    let teacherOptions = '';
    teachersList.forEach(teacher => {
        teacherOptions += `<option value="${teacher.name}" data-email="${teacher.email}">`;
    });
    
    const formHTML = `
        <form id="${formId}" class="email-form">
            <h4>📧 Contactar amb Professor/a</h4>
            <div class="form-field">
                <label>Nom del professor/a:</label>
                <input type="text" name="professor" required placeholder="Ex: Roger Codina" list="teachers-${formId}">
                <datalist id="teachers-${formId}">
                    ${teacherOptions}
                </datalist>
            </div>
            <div class="form-field">
                <label>Assumpte:</label>
                <select name="assumpte" required>
                    <option value="">Selecciona...</option>
                    <option value="reunio">Sol·licitar reunió</option>
                    <option value="consulta">Consulta acadèmica</option>
                    <option value="seguiment">Seguiment de l'alumne</option>
                    <option value="altre">Altre</option>
                </select>
            </div>
            <div class="form-field">
                <label>Missatge:</label>
                <textarea name="missatge" required placeholder="Escriu el teu missatge aquí..." rows="4"></textarea>
            </div>
            <div class="form-field">
                <label>Disponibilitat (opcional):</label>
                <input type="text" name="disponibilitat" placeholder="Ex: Dilluns i dimecres a la tarda">
            </div>
            
            <!-- Vista previa del email -->
            <div class="form-field email-preview" id="emailPreview-${formId}" style="display: none;">
                <label>📧 Correu de destinació:</label>
                <div class="email-info">
                    <span id="emailAddress-${formId}">professor@inscalaf.cat</span>
                </div>
            </div>
            
            <div class="form-actions">
                <button type="submit" class="btn-primary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                    </svg>
                    Enviar missatge
                </button>
                <button type="button" class="btn-secondary" onclick="cancelForm('${formId}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                    Cancel·lar
                </button>
            </div>
        </form>
    `;
    
    addMessage(formHTML, 'bot', true);
    
    // Manejar envío del formulario
    setTimeout(() => {
        const form = document.getElementById(formId);
        const professorInput = form.querySelector('input[name="professor"]');
        const emailPreview = document.getElementById(`emailPreview-${formId}`);
        const emailAddress = document.getElementById(`emailAddress-${formId}`);
        
        // Mostrar vista previa del correo cuando se selecciona un profesor
        professorInput.addEventListener('input', function() {
            const selectedName = this.value;
            const teacher = teachersList.find(t => t.name === selectedName);
            
            if (teacher) {
                emailAddress.textContent = teacher.email;
                emailPreview.style.display = 'block';
            } else if (selectedName.trim()) {
                // Generar email automáticamente para nombres no en la lista
                const autoEmail = selectedName.toLowerCase()
                    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // Eliminar acentos
                    .replace(/\s+/g, '.')
                    .replace(/[^a-z0-9.]/g, '') + '@inscalaf.cat';
                emailAddress.textContent = autoEmail;
                emailPreview.style.display = 'block';
            } else {
                emailPreview.style.display = 'none';
            }
        });
        
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);
                
                // Construir mensaje para enviar
                const message = `Contactar professor ${data.professor} - Assumpte: ${data.assumpte}, Missatge: ${data.missatge}${data.disponibilitat ? ', Disponibilitat: ' + data.disponibilitat : ''}`;
                
                // Deshabilitar el formulario con animación
                e.target.style.opacity = '0.5';
                e.target.querySelectorAll('input, textarea, button, select').forEach(el => el.disabled = true);
                
                // Añadir indicador de carga
                const submitBtn = e.target.querySelector('.btn-primary');
                submitBtn.innerHTML = '<span style="display: inline-block; animation: spin 1s linear infinite;">⏳</span> Enviant...';
                
                // Enviar al backend
                try {
                    const response = await getBotResponse(message);
                    addMessage(response, 'bot');
                    // Ocultar formulario después de enviar
                    e.target.style.display = 'none';
                } catch (error) {
                    addMessage("Ho sento, hi ha hagut un error. Si us plau, torna-ho a intentar.", 'bot');
                    // Reactivar formulario en caso de error
                    e.target.style.opacity = '1';
                    e.target.querySelectorAll('input, textarea, button, select').forEach(el => el.disabled = false);
                    submitBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg> Enviar missatge`;
                }
            });
        }
    }, 100);
}

// Función para cancelar formulario
function cancelForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.style.display = 'none';
        addMessage('Formulari cancel·lat. En què més et puc ajudar?', 'bot');
    }
}

// Función para mostrar formulario de justificación (acción rápida)
function showAbsenceForm() {
    addMessage('Vull justificar una falta', 'user');
    addMessage("Entenc que vols justificar una falta. Si us plau, omple aquest formulari:", 'bot');
    createAbsenceForm();
}

// Función para mostrar formulario de reunión (acción rápida)
function showMeetingForm() {
    addMessage('Vull sol·licitar una reunió amb un professor', 'user');
    addMessage("Vols contactar amb un professor. Si us plau, omple aquest formulari:", 'bot');
    createTeacherContactForm();
}

// Animación inicial al cargar la página
window.addEventListener('load', async () => {
    console.log('Chat carregat per a:', userData.nom);
    
    // Cargar lista de profesores
    await loadTeachersList();
    
    // Verificar elementos críticos
    console.log('Elements trobats:', {
        form: !!chatForm,
        input: !!messageInput,
        button: !!sendBtn,
        teachers: teachersList.length
    });
    
    // Asegurar que el botón esté deshabilitado al inicio
    if (sendBtn && messageInput) {
        sendBtn.disabled = !messageInput.value.trim();
    }
});

// Función para manejar el redimensionamiento de la ventana
window.addEventListener('resize', () => {
    const chatContainer = document.getElementById('chat-container');
    if (window.innerWidth < 768 && chatContainer) {
        chatContainer.style.height = '100vh';
    } else if (chatContainer) {
        chatContainer.style.height = '90vh';
    }
});

// Guardar conversación en localStorage
function saveConversation() {
    localStorage.setItem('riquer_chat_history', JSON.stringify({
        userData,
        messages: chatMessages,
        timestamp: new Date()
    }));
}

// Cargar conversación anterior (opcional)
function loadConversation() {
    const saved = localStorage.getItem('riquer_chat_history');
    if (saved) {
        const data = JSON.parse(saved);
        const hoursSince = (new Date() - new Date(data.timestamp)) / (1000 * 60 * 60);
        
        // Solo cargar si han pasado menos de 24 horas
        if (hoursSince < 24) {
            return data;
        }
    }
    return null;
}

// Auto-guardar conversación cada 5 minutos
setInterval(saveConversation, 5 * 60 * 1000);

// Guardar al salir de la página
window.addEventListener('beforeunload', saveConversation);

// Manejar errores globales
window.addEventListener('error', (e) => {
    console.error('Error global:', e.error);
});

// Inicializar tooltips si es necesario
document.querySelectorAll('[title]').forEach(element => {
    element.addEventListener('mouseenter', function() {
        this.style.cursor = 'help';
    });
});
