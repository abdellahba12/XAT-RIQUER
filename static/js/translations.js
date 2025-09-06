// translations.js - Sistema de traducción completo para el chat multilingüe
const translations = {
    ca: {
        // Header
        chatTitle: "Xat amb l'Institut Alexandre de Riquer",
        logout: "Tancar sessió",
        
        // Mensajes de bienvenida
        welcomeGreeting: "Hola {name}! 👋",
        welcomeIntro: "Sóc en Riquer, l'assistent virtual de l'Institut Alexandre de Riquer.",
        welcomeHelp: "Estic aquí per ajudar-te amb qualsevol consulta sobre l'institut. Pots preguntar-me sobre:",
        
        // Opciones del menú
        schedules: "Horaris i calendari escolar",
        teacherContact: "Contacte amb professors i tutors",
        absenceJustify: "Justificació de faltes",
        academicInfo: "Informació acadèmica",
        activities: "Activitats i serveis de l'institut",
        helpQuestion: "En què et puc ajudar?",
        
        // Input
        messagePlaceholder: "Escriu el teu missatge...",
        
        // Formularios
        absenceFormTitle: "📋 Justificació de Falta d'Assistència",
        studentName: "Nom de l'alumne:",
        courseGroup: "Curs i grup:",
        absenceDate: "Data de l'absència:",
        reason: "Motiu:",
        sendJustification: "Enviar justificació",
        cancel: "Cancel·lar",
        
        teacherFormTitle: "📧 Contactar amb Professor/a",
        teacherName: "Nom del professor/a:",
        subject: "Assumpte:",
        selectOption: "Selecciona...",
        requestMeeting: "Sol·licitar reunió",
        academicQuery: "Consulta acadèmica",
        studentFollowup: "Seguiment de l'alumne",
        other: "Altre",
        message: "Missatge:",
        availability: "Disponibilitat (si és per reunió):",
        sendMessage: "Enviar missatge",
        
        // Respuestas del bot
        typingIndicator: "En Riquer està escrivint...",
        understandAbsence: "Entenc que vols justificar una falta. Si us plau, omple aquest formulari:",
        understandContact: "Vols contactar amb un professor. Si us plau, omple aquest formulari:",
        formCancelled: "Formulari cancel·lat. En què més et puc ajudar?",
        errorSending: "Ho sento, hi ha hagut un error. Si us plau, torna-ho a intentar.",
        
        // Validaciones
        fillAllFields: "Si us plau, completa tots els camps obligatoris."
    },
    
    es: {
        // Header
        chatTitle: "Chat con el Instituto Alexandre de Riquer",
        logout: "Cerrar sesión",
        
        // Mensajes de bienvenida
        welcomeGreeting: "¡Hola {name}! 👋",
        welcomeIntro: "Soy Riquer, el asistente virtual del Instituto Alexandre de Riquer.",
        welcomeHelp: "Estoy aquí para ayudarte con cualquier consulta sobre el instituto. Puedes preguntarme sobre:",
        
        // Opciones del menú
        schedules: "Horarios y calendario escolar",
        teacherContact: "Contacto con profesores y tutores",
        absenceJustify: "Justificación de faltas",
        academicInfo: "Información académica",
        activities: "Actividades y servicios del instituto",
        helpQuestion: "¿En qué puedo ayudarte?",
        
        // Input
        messagePlaceholder: "Escribe tu mensaje...",
        
        // Formularios
        absenceFormTitle: "📋 Justificación de Falta de Asistencia",
        studentName: "Nombre del alumno:",
        courseGroup: "Curso y grupo:",
        absenceDate: "Fecha de la ausencia:",
        reason: "Motivo:",
        sendJustification: "Enviar justificación",
        cancel: "Cancelar",
        
        teacherFormTitle: "📧 Contactar con Profesor/a",
        teacherName: "Nombre del profesor/a:",
        subject: "Asunto:",
        selectOption: "Selecciona...",
        requestMeeting: "Solicitar reunión",
        academicQuery: "Consulta académica",
        studentFollowup: "Seguimiento del alumno",
        other: "Otro",
        message: "Mensaje:",
        availability: "Disponibilidad (si es para reunión):",
        sendMessage: "Enviar mensaje",
        
        // Respuestas del bot
        typingIndicator: "Riquer está escribiendo...",
        understandAbsence: "Entiendo que quieres justificar una falta. Por favor, rellena este formulario:",
        understandContact: "Quieres contactar con un profesor. Por favor, rellena este formulario:",
        formCancelled: "Formulario cancelado. ¿En qué más puedo ayudarte?",
        errorSending: "Lo siento, ha habido un error. Por favor, inténtalo de nuevo.",
        
        // Validaciones
        fillAllFields: "Por favor, completa todos los campos obligatorios."
    },
    
    ar: {
        // Header
        chatTitle: "محادثة مع معهد ألكسندر دي ريكير",
        logout: "تسجيل الخروج",
        
        // Mensajes de bienvenida
        welcomeGreeting: "مرحباً {name}! 👋",
        welcomeIntro: "أنا ريكير، المساعد الافتراضي لمعهد ألكسندر دي ريكير.",
        welcomeHelp: "أنا هنا لمساعدتك في أي استفسار حول المعهد. يمكنك أن تسألني عن:",
        
        // Opciones del menú
        schedules: "الجداول والتقويم المدرسي",
        teacherContact: "التواصل مع المعلمين والمرشدين",
        absenceJustify: "تبرير الغياب",
        academicInfo: "المعلومات الأكاديمية",
        activities: "الأنشطة والخدمات في المعهد",
        helpQuestion: "كيف يمكنني مساعدتك؟",
        
        // Input
        messagePlaceholder: "اكتب رسالتك...",
        
        // Formularios
        absenceFormTitle: "📋 تبرير الغياب",
        studentName: "اسم الطالب:",
        courseGroup: "الصف والمجموعة:",
        absenceDate: "تاريخ الغياب:",
        reason: "السبب:",
        sendJustification: "إرسال التبرير",
        cancel: "إلغاء",
        
        teacherFormTitle: "📧 التواصل مع المعلم",
        teacherName: "اسم المعلم:",
        subject: "الموضوع:",
        selectOption: "اختر...",
        requestMeeting: "طلب اجتماع",
        academicQuery: "استفسار أكاديمي",
        studentFollowup: "متابعة الطالب",
        other: "آخر",
        message: "الرسالة:",
        availability: "التوفر (إذا كان للاجتماع):",
        sendMessage: "إرسال الرسالة",
        
        // Respuestas del bot
        typingIndicator: "ريكير يكتب...",
        understandAbsence: "أفهم أنك تريد تبرير غياب. من فضلك، املأ هذا النموذج:",
        understandContact: "تريد التواصل مع معلم. من فضلك، املأ هذا النموذج:",
        formCancelled: "تم إلغاء النموذج. كيف يمكنني مساعدتك أيضاً؟",
        errorSending: "عذراً، حدث خطأ. من فضلك حاول مرة أخرى.",
        
        // Validaciones
        fillAllFields: "من فضلك، أكمل جميع الحقول المطلوبة."
    }
};

// Idioma actual
let currentLanguage = localStorage.getItem('chatLanguage') || 'ca';

// Función para obtener traducción
function t(key, params = {}) {
    let text = translations[currentLanguage][key] || translations['ca'][key] || key;
    
    // Reemplazar parámetros
    Object.keys(params).forEach(param => {
        text = text.replace(`{${param}}`, params[param]);
    });
    
    return text;
}

// Función para cambiar idioma
function changeLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('chatLanguage', lang);
    
    // Actualizar dirección del texto para árabe
    document.body.dir = lang === 'ar' ? 'rtl' : 'ltr';
    
    // Actualizar todos los textos de la interfaz
    updateUITranslations();
    
    // Notificar al backend del cambio de idioma
    if (window.updateBotLanguage) {
        window.updateBotLanguage(lang);
    }
}

// Función para actualizar las traducciones en la UI
function updateUITranslations() {
    // Actualizar título del chat
    const chatTitle = document.querySelector('.header-info h3');
    if (chatTitle) chatTitle.textContent = t('chatTitle');
    
    // Actualizar placeholder del input
    const messageInput = document.getElementById('message-input');
    if (messageInput) messageInput.placeholder = t('messagePlaceholder');
    
    // Actualizar botón de logout
    const logoutBtn = document.querySelector('.logout-btn span');
    if (logoutBtn) logoutBtn.textContent = t('logout');
    
    // Actualizar indicador de escritura
    const typingText = document.querySelector('.typing-indicator');
    if (typingText && typingText.textContent.includes('escribiendo') || typingText.textContent.includes('escrivint') || typingText.textContent.includes('يكتب')) {
        const spans = typingText.innerHTML.match(/<span><\/span>/g);
        if (spans) {
            typingText.innerHTML = spans.join('') + ' ' + t('typingIndicator');
        }
    }
    
    // Actualizar mensaje de bienvenida si existe
    updateWelcomeMessage();
}

// Función para actualizar el mensaje de bienvenida
function updateWelcomeMessage() {
    const welcomeMessage = document.querySelector('.welcome-message .message-content');
    if (welcomeMessage && window.userData) {
        const userName = window.userData.nom.split(' ')[0];
        welcomeMessage.innerHTML = `
            <p>${t('welcomeGreeting', { name: userName })}</p>
            <p>${t('welcomeIntro')}</p>
            <p>${t('welcomeHelp')}</p>
            <ul>
                <li>📅 ${t('schedules')}</li>
                <li>👨‍🏫 ${t('teacherContact')}</li>
                <li>📋 ${t('absenceJustify')}</li>
                <li>📚 ${t('academicInfo')}</li>
                <li>🏫 ${t('activities')}</li>
            </ul>
            <p>${t('helpQuestion')}</p>
        `;
    }
}

// Función para detectar idioma automáticamente (mejorada)
function autoDetectLanguage(text) {
    const lowerText = text.toLowerCase();
    
    // Detectar árabe por caracteres Unicode
    if (/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/.test(text)) {
        return 'ar';
    }
    
    // Palabras distintivas por idioma
    const catalanWords = ['què', 'com', 'quan', 'són', 'està', 'hem', 'bon', 'molt', 'professor', 'alumne', 'institut', 'bon dia', 'bona tarda'];
    const spanishWords = ['qué', 'cómo', 'cuándo', 'son', 'está', 'hemos', 'buen', 'mucho', 'profesor', 'alumno', 'instituto', 'buenos días', 'buenas tardes'];
    
    let catalanScore = 0;
    let spanishScore = 0;
    
    catalanWords.forEach(word => {
        if (lowerText.includes(word)) catalanScore += (word.length > 3 ? 2 : 1);
    });
    
    spanishWords.forEach(word => {
        if (lowerText.includes(word)) spanishScore += (word.length > 3 ? 2 : 1);
    });
    
    // Patrones específicos
    if (lowerText.includes('qué tal') || lowerText.includes('buenos días') || lowerText.includes('buenas tardes')) {
        spanishScore += 3;
    }
    
    if (lowerText.includes('com va') || lowerText.includes('bon dia') || lowerText.includes('bona tarda')) {
        catalanScore += 3;
    }
    
    if (spanishScore > catalanScore) return 'es';
    if (catalanScore > spanishScore) return 'ca';
    
    return currentLanguage; // Mantener idioma actual si no está claro
}

// Función mejorada para enviar mensajes
function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Detectar idioma automáticamente si no hay selección manual
    const detectedLanguage = autoDetectLanguage(message);
    if (detectedLanguage !== currentLanguage) {
        changeLanguage(detectedLanguage);
    }
    
    // Agregar prefijo de idioma al mensaje
    const languagePrefix = {
        'ca': '[CA] ',
        'es': '[ES] ',
        'ar': '[AR] '
    };
    
    const messageWithLanguage = languagePrefix[currentLanguage] + message;
    
    // Limpiar input
    messageInput.value = '';
    
    // Mostrar mensaje del usuario
    addMessageToChat('user', message);
    
    // Mostrar indicador de escritura
    showTypingIndicator();
    
    // Enviar al backend
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: messageWithLanguage,
            user_name: window.userData.nom,
            user_contact: window.userData.contacte,
            language: currentLanguage
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTypingIndicator();
        
        if (data.response) {
            addMessageToChat('bot', data.response);
        } else if (data.error) {
            addMessageToChat('bot', t('errorSending'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        hideTypingIndicator();
        addMessageToChat('bot', t('errorSending'));
    });
}

// Función para enviar formulario de ausencias
function sendAbsenceForm() {
    const formData = {
        alumne: document.getElementById('student-name').value.trim(),
        curs: document.getElementById('course-group').value.trim(),
        data: document.getElementById('absence-date').value.trim(),
        motiu: document.getElementById('reason').value.trim()
    };
    
    // Validar campos obligatorios
    if (!formData.alumne || !formData.curs || !formData.data || !formData.motiu) {
        alert(t('fillAllFields'));
        return;
    }
    
    // Construir mensaje con prefijo de idioma
    const languagePrefix = {
        'ca': '[CA] ',
        'es': '[ES] ',
        'ar': '[AR] '
    };
    
    const message = `${languagePrefix[currentLanguage]}Justificar falta - Alumne: ${formData.alumne}, Curs: ${formData.curs}, Data: ${formData.data}, Motiu: ${formData.motiu}`;
    
    // Cerrar modal
    closeModal('absence-modal');
    
    // Mostrar en chat
    addMessageToChat('user', `${t('absenceFormTitle')}: ${formData.alumne} - ${formData.data}`);
    showTypingIndicator();
    
    // Enviar al backend
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            user_name: window.userData.nom,
            user_contact: window.userData.contacte,
            language: currentLanguage
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTypingIndicator();
        addMessageToChat('bot', data.response || t('errorSending'));
    })
    .catch(error => {
        console.error('Error:', error);
        hideTypingIndicator();
        addMessageToChat('bot', t('errorSending'));
    });
}

// Función para enviar formulario de contacto con profesores
function sendTeacherForm() {
    const formData = {
        professor: document.getElementById('teacher-select').value.trim(),
        assumpte: document.getElementById('subject-select').value.trim(),
        missatge: document.getElementById('message-text').value.trim(),
        disponibilitat: document.getElementById('availability').value.trim()
    };
    
    // Validar campos obligatorios
    if (!formData.professor || !formData.assumpte || !formData.missatge) {
        alert(t('fillAllFields'));
        return;
    }
    
    // Construir mensaje con prefijo de idioma
    const languagePrefix = {
        'ca': '[CA] ',
        'es': '[ES] ',
        'ar': '[AR] '
    };
    
    const message = `${languagePrefix[currentLanguage]}Contactar professor ${formData.professor} - Assumpte: ${formData.assumpte}, Missatge: ${formData.missatge}, Disponibilitat: ${formData.disponibilitat || 'No especificada'}`;
    
    // Cerrar modal
    closeModal('teacher-modal');
    
    // Mostrar en chat
    addMessageToChat('user', `${t('teacherFormTitle')}: ${formData.professor}`);
    showTypingIndicator();
    
    // Enviar al backend
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            user_name: window.userData.nom,
            user_contact: window.userData.contacte,
            language: currentLanguage
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTypingIndicator();
        addMessageToChat('bot', data.response || t('errorSending'));
    })
    .catch(error => {
        console.error('Error:', error);
        hideTypingIndicator();
        addMessageToChat('bot', t('errorSending'));
    });
}

// Inicializar cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    // Configurar dirección del texto según el idioma
    document.body.dir = currentLanguage === 'ar' ? 'rtl' : 'ltr';
    
    // Actualizar traducciones iniciales
    updateUITranslations();
    
    // Agregar listener para Enter en el input de mensaje
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});

// Exportar funciones globales
window.translations = translations;
window.t = t;
window.changeLanguage = changeLanguage;
window.currentLanguage = currentLanguage;
window.sendMessage = sendMessage;
window.sendAbsenceForm = sendAbsenceForm;
window.sendTeacherForm = sendTeacherForm;
window.autoDetectLanguage = autoDetectLanguage;
