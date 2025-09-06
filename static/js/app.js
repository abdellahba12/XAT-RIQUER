// Variables globales
let chatMessages = [];
let teachersList = [];

// userData ja ve definit en el HTML des del servidor
// const userData = { nom: "...", contacte: "..." };

// Elementos del DOM
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const chatMessagesDiv = document.getElementById('chat-messages');
const typingIndicator = document.querySelector('.typing-indicator');

// Obtener el botón de enviar correctamente
const sendBtn = document.querySelector('.send-btn');

// Verificar que los elementos existen
if (!chatForm || !messageInput || !sendBtn) {
    console.error('Error: No se encontraron elementos del DOM necesarios');
}

// Funció per carregar la llista de professors al inicialitzar
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
    
    // Añadir prefijo de idioma si es árabe o español
    let finalMessage = message;
    if (currentLanguage === 'ar') {
        finalMessage = '[AR] ' + message;
    } else if (currentLanguage === 'es') {
        finalMessage = '[ES] ' + message;
    }
    
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
        addMessage(t('understandAbsence'), 'bot');
        createAbsenceForm();
    } else if (intent === 'teacher_contact') {
        // Mostrar formulario de contacto
        addMessage(t('understandContact'), 'bot');
        createTeacherContactForm();
    } else {
        // Mostrar indicador de escritura y obtener respuesta normal
        showTypingIndicator();
        
        try {
            const response = await getBotResponse(finalMessage);
            hideTypingIndicator();
            addMessage(response, 'bot');
        } catch (error) {
            hideTypingIndicator();
            addMessage(t('errorSending'), 'bot');
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
        // Usar la inicial del nombre del usuario autenticado
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

// Función para formatear mensajes (detectar enlaces, saltos de línea, etc.)
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

// Función para obtener respuesta del bot desde el servidor Flask
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
    
    if (lowerMessage.includes('horari') || lowerMessage.includes('horaris')) {
        return `Els horaris de l'institut són:
        
📅 **Horari lectiu:**
- ESO: 8:00 - 14:30
- Batxillerat: 8:00 - 14:30

📞 **Horari d'atenció:**
- Horari lectiu: matins de 8,00 a 14,35.
- Horari d'atenció al públic: de dilluns a divendres de 8 a 14h

Necessites informació sobre algun horari específic?`;
    }
    
    if (lowerMessage.includes('tutor') || lowerMessage.includes('professor')) {
        return `Per contactar amb un tutor o professor, necessito saber:

1. El nom del professor/tutor
2. El curs de l'alumne
3. El motiu de la consulta

Amb aquesta informació podré generar un correu electrònic formal per enviar-lo al professor corresponent. Quin professor vols contactar?`;
    }
    
    if (lowerMessage.includes('falta') || lowerMessage.includes('justificar')) {
        return `Per justificar una falta d'assistència, necessito:

📋 Les següents dades:
- Nom i cognoms de l'alumne
- Curs i grup
- Data/es de l'absència
- Motiu de la falta

Generaré automàticament un correu a consergeria@gmail.com amb aquesta informació. Vols que procedeixi?`;
    }
    
    if (lowerMessage.includes('contacte') || lowerMessage.includes('contactar')) {
        return `📞 **Dades de contacte de l'Institut:**

📍 Adreça: C. Sant Joan Bta. de la Salle 6-8 08280 Calaf (Anoia)
📞 Telèfon: 93 868 04 14

📧 Email general: iescalaf@xtec.cat
🌐 Web: http://www.inscalaf.cat

En què més et puc ajudar?`;
    }
    
    // Respuesta por defecto
    return `Entenc que necessites ajuda amb: "${message}". 

Puc ajudar-te amb:
- 📅 Horaris i calendari
- 👨‍🏫 Contacte amb professors
- 📋 Justificació de faltes
- 📚 Informació acadèmica
- 🏫 Activitats de l'institut

Si us plau, especifica més la teva consulta perquè pugui ajudar-te millor.`;
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
            <h4>${t('absenceFormTitle')}</h4>
            <div class="form-field" style="animation-delay: 0.1s">
                <label>${t('studentName')}</label>
                <input type="text" name="alumne" required placeholder="Ex: Maria García Pérez" autocomplete="name">
            </div>
            <div class="form-field" style="animation-delay: 0.2s">
                <label>${t('courseGroup')}</label>
                <input type="text" name="curs" required placeholder="Ex: 2n ESO A" list="courses">
                <datalist id="courses">
                    <option value="1r ESO A">
                    <option value="1r ESO B">
                    <option value="2n ESO A">
                    <option value="2n ESO B">
                    <option value="3r ESO A">
                    <option value="3r ESO B">
                    <option value="4t ESO A">
                    <option value="4t ESO B">
                    <option value="1r Batxillerat">
                    <option value="2n Batxillerat">
                </datalist>
            </div>
            <div class="form-field" style="animation-delay: 0.3s">
                <label>${t('absenceDate')}</label>
                <input type="date" name="data" required value="${today}" max="${today}">
            </div>
            <div class="form-field" style="animation-delay: 0.4s">
                <label>${t('reason')}</label>
                <textarea name="motiu" required placeholder="Ex: Visita mèdica programada" rows="3"></textarea>
            </div>
            <div class="form-actions" style="animation-delay: 0.5s">
                <button type="submit" class="btn-primary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                    </svg>
                    ${t('sendJustification')}
                </button>
                <button type="button" class="btn-secondary" onclick="cancelForm('${formId}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                       <line x1="6" y1="6" x2="18" y2="18"></line>
                   </svg>
                   ${t('cancel')}
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
                   addMessage(t('errorSending'), 'bot');
                   // Reactivar formulario en caso de error
                   e.target.style.opacity = '1';
                   e.target.querySelectorAll('input, textarea, button').forEach(el => el.disabled = false);
                   submitBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg> ${t('sendJustification')}`;
               }
           });
       }
   }, 100);
}

// Función para crear formulario de contacto con profesor
function createTeacherContactForm() {
    const formId = 'teacher-form-' + Date.now();
    
    // Generar opciones del datalist amb la llista carregada
    let teacherOptions = '';
    teachersList.forEach(teacher => {
        teacherOptions += `<option value="${teacher.name}" data-email="${teacher.email}">`;
    });
    
    const formHTML = `
        <form id="${formId}" class="email-form">
            <h4>${t('teacherFormTitle')}</h4>
            <div class="form-field" style="animation-delay: 0.1s">
                <label>${t('teacherName')}</label>
                <input type="text" name="professor" required placeholder="Ex: Roger Codina" list="teachers-${formId}">
                <datalist id="teachers-${formId}">
                    ${teacherOptions}
                </datalist>
            </div>
            <div class="form-field" style="animation-delay: 0.2s">
                <label>${t('subject')}</label>
                <select name="assumpte" required>
                    <option value="">${t('selectOption')}</option>
                    <option value="reunio">${t('requestMeeting')}</option>
                    <option value="consulta">${t('academicQuery')}</option>
                    <option value="seguiment">${t('studentFollowup')}</option>
                    <option value="altre">${t('other')}</option>
                </select>
            </div>
            <div class="form-field" style="animation-delay: 0.3s">
                <label>${t('message')}</label>
                <textarea name="missatge" required placeholder="${currentLanguage === 'ar' ? 'اكتب رسالتك هنا...' : currentLanguage === 'es' ? 'Escribe tu mensaje aquí...' : 'Escriu el teu missatge aquí...'}" rows="4"></textarea>
            </div>
            <div class="form-field" style="animation-delay: 0.4s">
                <label>${t('availability')}</label>
                <input type="text" name="disponibilitat" placeholder="${currentLanguage === 'ar' ? 'مثال: الإثنين والأربعاء بعد الظهر' : currentLanguage === 'es' ? 'Ej: Lunes y miércoles por la tarde' : 'Ex: Dilluns i dimecres a la tarda'}">
            </div>
            
            <!-- Vista previa del correu que s'enviarà -->
            <div class="form-field email-preview" id="emailPreview-${formId}" style="display: none; animation-delay: 0.5s">
                <label>📧 Correu de destinació:</label>
                <div class="email-info">
                    <span id="emailAddress-${formId}">professor@inscalaf.cat</span>
                </div>
            </div>
            
            <div class="form-actions" style="animation-delay: 0.6s">
                <button type="submit" class="btn-primary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                    </svg>
                    ${t('sendMessage')}
                </button>
                <button type="button" class="btn-secondary" onclick="cancelForm('${formId}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                    ${t('cancel')}
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
        
        // Mostrar vista previa del correu quan es selecciona un professor
        professorInput.addEventListener('input', function() {
            const selectedName = this.value;
            const teacher = teachersList.find(t => t.name === selectedName);
            
            if (teacher) {
                emailAddress.textContent = teacher.email;
                emailPreview.style.display = 'block';
            } else if (selectedName.trim()) {
                // Generar email automàticament per noms que no estan a la llista
                const autoEmail = selectedName.toLowerCase()
                    .replace(' ', '.')
                    .replace(/[àáâã]/g, 'a')
                    .replace(/[èéêë]/g, 'e')
                    .replace(/[ìíîï]/g, 'i')
                    .replace(/[òóôõ]/g, 'o')
                    .replace(/[ùúûü]/g, 'u')
                    .replace(/ç/g, 'c') + '@inscalaf.cat';
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
                    addMessage(t('errorSending'), 'bot');
                    // Reactivar formulario en caso de error
                    e.target.style.opacity = '1';
                    e.target.querySelectorAll('input, textarea, button, select').forEach(el => el.disabled = false);
                    submitBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg> ${t('sendMessage')}`;
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
    addMessage(currentLanguage === 'ar' ? 'أريد تبرير غياب' : 
               currentLanguage === 'es' ? 'Quiero justificar una falta' : 
               'Vull justificar una falta', 'user');
    addMessage(t('understandAbsence'), 'bot');
    createAbsenceForm();
}

// Función para mostrar formulario de reunión (acción rápida)
function showMeetingForm() {
    addMessage(currentLanguage === 'ar' ? 'أريد طلب اجتماع مع معلم' : 
               currentLanguage === 'es' ? 'Quiero solicitar una reunión con un profesor' : 
               'Vull sol·licitar una reunió amb un professor', 'user');
    addMessage(t('understandContact'), 'bot');
    createTeacherContactForm();
}

// Detectar intenciones en el mensaje
function detectIntent(message) {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('justificar') || lowerMessage.includes('falta') || lowerMessage.includes('absència')) {
        return 'absence';
    } else if (lowerMessage.includes('contactar') || lowerMessage.includes('professor') || lowerMessage.includes('tutor') || lowerMessage.includes('reunió')) {
        return 'teacher_contact';
    }
    
    return null;
}

// Animación inicial
window.addEventListener('load', async () => {
    console.log('Chat carregat per a:', userData.nom);
    
    // Carregar llista de professors
    await loadTeachersList();
    
    // Verificar elementos críticos
    console.log('Elementos encontrados:', {
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
    if (window.innerWidth < 768) {
        chatContainer.style.height = '100vh';
    } else {
        chatContainer.style.height = '90vh';
    }
});

// Función para detectar y manejar menciones de correos para profesores
function checkForEmailGeneration(message) {
    const emailKeywords = ['enviar correu', 'contactar', 'reunió', 'cita', 'parlar amb'];
    const hasEmailIntent = emailKeywords.some(keyword => 
        message.toLowerCase().includes(keyword)
    );
    
    if (hasEmailIntent) {
        console.log('Detectada intención de enviar email');
    }
}

// Guardar conversación en localStorage (opcional)
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

// Función para exportar conversación
function exportConversation() {
    const conversationText = chatMessages.map(msg => {
        const time = new Date(msg.timestamp).toLocaleString('ca-ES');
        const sender = msg.sender === 'user' ? userData.nom : 'Riquer';
        return `[${time}] ${sender}: ${msg.text}`;
    }).join('\n\n');
    
    const blob = new Blob([conversationText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversa_riquer_${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
}

// Función para limpiar conversación
function clearConversation() {
    if (confirm('Estàs segur que vols esborrar tota la conversa?')) {
        chatMessages = [];
        const messages = chatMessagesDiv.querySelectorAll('.message');
        messages.forEach(msg => msg.remove());
        localStorage.removeItem('riquer_chat_history');
    }
}

// Función para mostrar ayuda
function showHelp() {
    addMessage(`🔍 **Com puc ajudar-te:**

**Comandes ràpides:**
- "Horaris" → Consultar horaris
- "Contactar [nom professor]" → Enviar email
- "Justificar falta" → Justificar absència
- "Calendari" → Veure calendari escolar
- "Activitats" → Activitats extraescolars

**Funcions especials:**
- Puc generar correus automàticament
- Puc proporcionar informació de contacte

Escriu la teva pregunta de forma natural!`, 'bot');
}

// Auto-guardar conversación cada 5 minutos
setInterval(saveConversation, 5 * 60 * 1000);

// Guardar al salir de la página
window.addEventListener('beforeunload', saveConversation);
