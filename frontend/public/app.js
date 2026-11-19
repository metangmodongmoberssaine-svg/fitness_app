/**
 * Application Frontend Vue 3 - Real-Time AI Fitness Counter
 * Conforme au dossier de conception UML :
 * - Use Cases : Visiteur, Sportif, Administrateur, Service de notification
 * - Diagramme de Séquence (Figures 4, 5, 6)
 * - Diagramme d'Activité (Figure 7)
 * - Traitement d'images local (MediaPipe Pose 33 points clés, calcul d'angles vectoriels, hystérésis)
 */
const { createApp, ref, reactive, computed, onMounted, onBeforeUnmount, watch } = Vue;

const API_BASE = "http://localhost:8000/api";

const app = createApp({
  setup() {
    // État utilisateur & navigation
    const activeView = ref("catalogue"); // Initialement sur le catalogue pour les visiteurs
    const currentUser = ref({
      id: 0,
      nom: "Visiteur",
      prenom: "Visiteur",
      email: "",
      role: "visiteur",
      poids: 70.0,
      taille: 175.0,
      niveau: "Débutant"
    });

    const isAuthModalOpen = ref(false);
    const isProfileModalOpen = ref(false);
    const isShareModalOpen = ref(false);
    const isDetailModalOpen = ref(false);
    const isNewExoModalOpen = ref(false);
    const isNewObjModalOpen = ref(false);

    // Formulaire d'authentification et état UI
    const authPromptReason = ref("");
    const showPassword = ref(false);
    const authMessage = ref("");
    const authMessageType = ref("info");

    const authForm = reactive({
      mode: "login", // 'login' ou 'register'
      nom: "",
      prenom: "",
      email: "",
      mot_de_passe: "",
      role: "sportif",
      poids: 70.0,
      taille: 175.0,
      niveau: "Intermédiaire"
    });

    // Données Catalogue & Exercices
    const catalogue = ref([]);
    const selectedExercice = ref(null);
    const selectedVideoSource = ref("webcam"); // 'webcam', 'sample', 'file'
    const sampleVideos = ref([]);
    const selectedSampleFile = ref("");

    // État Séance d'entraînement en direct
    const sessionState = reactive({
      statut: "non_demarre", // 'non_demarre', 'en_cours', 'en_pause', 'terminee'
      idSeance: null,
      totalRepetitions: 0,
      angleCourant: 0,
      phaseCourante: "haute", // 'haute', 'basse', 'transition'
      dureeSecondes: 0,
      calories: 0,
      personneDetectee: true,
      derniereCorrection: null,
      historiqueRepetitions: [],
      historiqueCorrections: [],
      repJusteIncr: false,
      fps: 0
    });

    const recapitulatifSeance = ref(null);
    const detailSeance = ref(null);

    // Objectifs, Historique, Notifications & Admin
    const objectifs = ref([]);
    const historiqueSeances = ref([]);
    const notifications = ref([]);
    const isNotifOpen = ref(false);
    const adminUsers = ref([]);
    const adminStats = ref({});

    // Nouveaux formulaires
    const nouvelObjectif = reactive({
      exercice_id: 1,
      repetitions_cible: 20,
      periode: "quotidien",
      date_limite: ""
    });

    const nouvelExercice = reactive({
      id: null,
      nom: "",
      description: "",
      groupe_musculaire: "",
      difficulte: 1,
      video_sample: "",
      regle: {
        articulation_cle: "genou",
        angle_haut: 160.0,
        angle_bas: 90.0,
        tolerance: 10.0,
        duree_min_repetition: 600
      }
    });

    // Références DOM Médias & Vision
    const videoElement = ref(null);
    const canvasElement = ref(null);
    let cameraInstance = null;
    let poseDetector = null;
    let timerInterval = null;
    let fpsFrames = 0;
    let lastFpsTime = Date.now();
    let audioCtx = null;

    // Variables machine à états comptage local
    let minAngleObserved = 999;
    let maxAngleObserved = 0;
    let repStartTime = 0;
    let lastCorrectionTime = 0;

    // --- SONS & SYNTHÈSE VOCALE ---
    const initAudio = () => {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
    };

    const playRepChime = () => {
      try {
        initAudio();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // Ré5
        osc.frequency.exponentialRampToValueAtTime(880.00, audioCtx.currentTime + 0.15); // La5
        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.3);
      } catch (e) {
        console.warn("Audio non supporté:", e);
      }
    };

    const speakPostureCorrection = (message) => {
      if ("speechSynthesis" in window) {
        const now = Date.now();
        if (now - lastCorrectionTime > 3500) { // Éviter de parler en continu
          lastCorrectionTime = now;
          const utter = new SpeechSynthesisUtterance(message);
          utter.lang = "fr-FR";
          utter.rate = 1.05;
          window.speechSynthesis.speak(utter);
        }
      }
    };

    // --- REQUÊTES API ---
    const loadCatalogue = async () => {
      try {
        const res = await fetch(`${API_BASE}/exercices`);
        catalogue.value = await res.json();
        if (catalogue.value.length > 0 && !selectedExercice.value) {
          selectedExercice.value = catalogue.value[0];
          nouvelObjectif.exercice_id = catalogue.value[0].id;
        }
      } catch (e) {
        console.error("Erreur chargement catalogue:", e);
      }
    };

    const loadSamples = async () => {
      try {
        const res = await fetch(`${API_BASE}/vision/samples`);
        sampleVideos.value = await res.json();
        if (sampleVideos.value.length > 0) {
          selectedSampleFile.value = sampleVideos.value[0].url;
        }
      } catch (e) {
        console.error("Erreur chargement samples:", e);
      }
    };

    const loadObjectifs = async () => {
      if (!currentUser.value || currentUser.value.role === "visiteur") return;
      try {
        const res = await fetch(`${API_BASE}/objectifs?sportif_id=${currentUser.value.id}`);
        objectifs.value = await res.json();
      } catch (e) {
        console.error("Erreur chargement objectifs:", e);
      }
    };

    const loadHistorique = async () => {
      if (!currentUser.value || currentUser.value.role === "visiteur") return;
      try {
        const res = await fetch(`${API_BASE}/seances/historique?sportif_id=${currentUser.value.id}`);
        historiqueSeances.value = await res.json();
      } catch (e) {
        console.error("Erreur chargement historique:", e);
      }
    };

    const loadNotifications = async () => {
      if (!currentUser.value || currentUser.value.role === "visiteur") return;
      try {
        const res = await fetch(`${API_BASE}/notifications?sportif_id=${currentUser.value.id}`);
        notifications.value = await res.json();
      } catch (e) {
        console.error("Erreur chargement notifications:", e);
      }
    };

    const loadAdminData = async () => {
      if (!currentUser.value || currentUser.value.role !== "administrateur") return;
      try {
        const [usersRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/admin/users`),
          fetch(`${API_BASE}/admin/statistiques`)
        ]);
        adminUsers.value = await usersRes.json();
        adminStats.value = await statsRes.json();
      } catch (e) {
        console.error("Erreur admin:", e);
      }
    };

    // --- SÉLECTION EXERCICE ---
    const choisirExercice = async (exo) => {
      try {
        // GET /exercices/{id} (Figure 4, messages 2 à 5)
        const res = await fetch(`${API_BASE}/exercices/${exo.id}`);
        selectedExercice.value = await res.json();
      } catch (e) {
        selectedExercice.value = exo;
      }

      if (!currentUser.value || currentUser.value.role === "visiteur") {
        ouvrirAuth("login", `Connectez-vous ou créez un compte pour démarrer « ${exo.nom} » avec le suivi IA en temps réel.`);
      } else {
        activeView.value = "workout";
      }
    };

    // --- CALCULS GÉOMÉTRIQUES & VISION (LOCAL EMBARQUÉ) ---
    // Formule : θ = arccos[(BA · BC) / (|BA| × |BC|)]
    const calculateAngle = (ptA, ptB, ptC) => {
      if (!ptA || !ptB || !ptC) return 180;
      const ba_x = ptA.x - ptB.x;
      const ba_y = ptA.y - ptB.y;
      const bc_x = ptC.x - ptB.x;
      const bc_y = ptC.y - ptB.y;

      const dotProduct = ba_x * bc_x + ba_y * bc_y;
      const normBA = Math.sqrt(ba_x * ba_x + ba_y * ba_y);
      const normBC = Math.sqrt(bc_x * bc_x + bc_y * bc_y);

      if (normBA * normBC === 0) return 180;
      let cosTheta = dotProduct / (normBA * normBC);
      cosTheta = Math.max(-1, Math.min(1, cosTheta));
      return (Math.acos(cosTheta) * 180) / Math.PI;
    };

    // Initialisation MediaPipe Pose
    const initPoseDetector = () => {
      if (typeof Pose === "undefined") {
        console.warn("MediaPipe Pose CDN non chargé, basculement en mode simulation/test vidéo.");
        return null;
      }
      const pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
      });
      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      pose.onResults(onPoseResults);
      return pose;
    };

    // Callback de traitement trame par trame (Figure 5 - Phase 2)
    const onPoseResults = (results) => {
      if (sessionState.statut !== "en_cours") return;

      // Calcul FPS
      fpsFrames++;
      const now = Date.now();
      if (now - lastFpsTime >= 1000) {
        sessionState.fps = fpsFrames;
        fpsFrames = 0;
        lastFpsTime = now;
      }

      const canvas = canvasElement.value;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const video = videoElement.value;

      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;

      ctx.save();
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (!results.poseLandmarks) {
        // Signalisation personne non détectée (Figure 5, messages 9-10)
        sessionState.personneDetectee = false;
        ctx.restore();
        return;
      }

      sessionState.personneDetectee = true;
      const lm = results.poseLandmarks;

      // Dessin des repères squelettiques
      if (typeof drawConnectors !== "undefined" && typeof drawLandmarks !== "undefined") {
        drawConnectors(ctx, lm, POSE_CONNECTIONS, { color: "#06b6d4", lineWidth: 3 });
        drawLandmarks(ctx, lm, { color: "#10b981", lineWidth: 2, radius: 4 });
      }

      // Extraction de l'articulation suivie selon la règle de comptage de l'exercice
      const regle = selectedExercice.value?.regle || {
        articulation_cle: "genou",
        angle_haut: 165.0,
        angle_bas: 90.0,
        tolerance: 10.0,
        duree_min_repetition: 600
      };

      const art = (regle.articulation_cle || "genou").toLowerCase();
      let currentAngle = 180;

      if (art.includes("genou")) {
        // Squats : hanche(23/24) - genou(25/26) - cheville(27/28)
        const angleG = calculateAngle(lm[23], lm[25], lm[27]);
        const angleD = calculateAngle(lm[24], lm[26], lm[28]);
        currentAngle = (angleG + angleD) / 2;
        highlightJoint(ctx, lm[25], canvas.width, canvas.height, currentAngle);
        highlightJoint(ctx, lm[26], canvas.width, canvas.height, currentAngle);
      } else if (art.includes("coude") || art.includes("pompe") || art.includes("biceps")) {
        // Pompes / Curls / Tractions : épaule(11/12) - coude(13/14) - poignet(15/16)
        const angleG = calculateAngle(lm[11], lm[13], lm[15]);
        const angleD = calculateAngle(lm[12], lm[14], lm[16]);
        currentAngle = (angleG + angleD) / 2;
        highlightJoint(ctx, lm[13], canvas.width, canvas.height, currentAngle);
        highlightJoint(ctx, lm[14], canvas.width, canvas.height, currentAngle);
      } else if (art.includes("distance") || art.includes("chest")) {
        // Écarté machine : distance horizontale poignets
        const dist = Math.abs((lm[15].x - lm[16].x) * canvas.width);
        currentAngle = dist;
      }

      sessionState.angleCourant = Math.round(currentAngle);

      // Traitement dans la machine à états de comptage (CompteurRepetitions)
      traiterDecompteLocal(currentAngle, regle);

      ctx.restore();
    };

    const highlightJoint = (ctx, point, width, height, angle) => {
      if (!point) return;
      const x = point.x * width;
      const y = point.y * height;
      ctx.beginPath();
      ctx.arc(x, y, 10, 0, 2 * Math.PI);
      ctx.fillStyle = "#38bdf8";
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.font = "bold 14px Inter, sans-serif";
      ctx.fillStyle = "#ffffff";
      ctx.fillText(`${Math.round(angle)}°`, x + 15, y - 5);
    };

    // Machine à états à 2 phases avec seuils d'hystérésis (Figure 5)
    const traiterDecompteLocal = (valeur, regle) => {
      const now = Date.now();
      const aHaut = regle.angle_haut;
      const aBas = regle.angle_bas;
      const tol = regle.tolerance || 10;
      const dureeMin = regle.duree_min_repetition || 600;

      if (valeur < minAngleObserved) minAngleObserved = valeur;
      if (valeur > maxAngleObserved) maxAngleObserved = valeur;

      // Détection des erreurs de posture (Contrôle posture Figure 5 & 7)
      if (aHaut > aBas) {
        if (sessionState.phaseCourante === "basse" && valeur > (aBas + tol * 2.2)) {
          const msg = "Descendez plus bas pour une répétition complète !";
          emettreCorrection(msg, 1);
        } else if (valeur < (aBas - 25)) {
          const msg = "Attention à l'hyperflexion, ne descendez pas trop bas !";
          emettreCorrection(msg, 2);
        }
      }

      // Logique Hystérésis
      if (aHaut > aBas) {
        // Cas standard (Squats, Pompes, Dumbbells)
        if (sessionState.phaseCourante === "haute") {
          if (valeur <= (aBas + tol)) {
            sessionState.phaseCourante = "basse";
            repStartTime = now;
          }
        } else if (sessionState.phaseCourante === "basse") {
          if (valeur >= (aHaut - tol)) {
            // Cycle haut -> bas -> haut validé !
            const dureeMs = now - repStartTime;
            if (dureeMs >= dureeMin) {
              validerRepetition(dureeMs, Math.abs(maxAngleObserved - minAngleObserved));
            }
            sessionState.phaseCourante = "haute";
            minAngleObserved = 999;
            maxAngleObserved = 0;
          }
        }
      } else {
        // Cas inversé (ex: distance poignets écarté)
        if (sessionState.phaseCourante === "haute") {
          if (valeur >= (aBas - tol)) {
            sessionState.phaseCourante = "basse";
            repStartTime = now;
          }
        } else if (sessionState.phaseCourante === "basse") {
          if (valeur <= (aHaut + tol)) {
            const dureeMs = now - repStartTime;
            if (dureeMs >= dureeMin) {
              validerRepetition(dureeMs, Math.abs(maxAngleObserved - minAngleObserved));
            }
            sessionState.phaseCourante = "haute";
            minAngleObserved = 999;
            maxAngleObserved = 0;
          }
        }
      }
    };

    const validerRepetition = (dureeMs, amplitude) => {
      sessionState.totalRepetitions++;
      playRepChime();

      // Effet visuel
      sessionState.repJusteIncr = true;
      setTimeout(() => { sessionState.repJusteIncr = false; }, 350);

      const nouvelleRep = {
        numero: sessionState.totalRepetitions,
        horodatage: Date.now() / 1000,
        duree_ms: dureeMs,
        amplitude: Math.round(amplitude),
        est_correcte: true
      };
      sessionState.historiqueRepetitions.push(nouvelleRep);

      // Calcul dynamique des calories
      const poids = currentUser.value?.poids || 70;
      sessionState.calories = Math.round(
        (sessionState.totalRepetitions * 0.35 + (sessionState.dureeSecondes / 60) * 1.5 * (poids / 70)) * 10
      ) / 10;
    };

    const emettreCorrection = (message, gravite) => {
      sessionState.derniereCorrection = { message, gravite };
      speakPostureCorrection(message);

      const corr = {
        message,
        gravite,
        type: "mixte",
        horodatage: Date.now() / 1000
      };
      // Éviter d'accumuler les doublons
      if (!sessionState.historiqueCorrections.some(c => c.message === message && Math.abs(c.horodatage - corr.horodatage) < 3)) {
        sessionState.historiqueCorrections.push(corr);
      }
    };

    // --- CYCLE DE VIE DE LA SÉANCE (Figures 4, 6 & 7) ---
    const lancerSeance = async () => {
      if (!currentUser.value || currentUser.value.role === "visiteur") {
        ouvrirAuth("login", "Connectez-vous pour lancer une séance et enregistrer votre historique.");
        return;
      }
      if (!selectedExercice.value) return;

      // 1. Initialiser la séance sur le serveur : POST /seances (Figure 4, msg 14-17)
      try {
        const res = await fetch(`${API_BASE}/seances`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sportif_id: currentUser.value.id,
            exercice_id: selectedExercice.value.id,
            objectif_id: null
          })
        });
        const data = await res.json();
        sessionState.idSeance = data.idSeance;
      } catch (e) {
        console.error("Erreur création séance:", e);
        sessionState.idSeance = Math.floor(Math.random() * 1000) + 1;
      }

      // 2. Activer la caméra et le flux vidéo (Figure 4, msg 9-11)
      sessionState.statut = "en_cours";
      sessionState.totalRepetitions = 0;
      sessionState.dureeSecondes = 0;
      sessionState.calories = 0;
      sessionState.historiqueRepetitions = [];
      sessionState.historiqueCorrections = [];
      minAngleObserved = 999;
      maxAngleObserved = 0;

      // Démarre le chronomètre
      timerInterval = setInterval(() => {
        if (sessionState.statut === "en_cours") {
          sessionState.dureeSecondes++;
        }
      }, 1000);

      await demarrerFluxVideo();
    };

    const demarrerFluxVideo = async () => {
      const video = videoElement.value;
      if (!video) return;

      poseDetector = initPoseDetector();

      if (selectedVideoSource.value === "webcam") {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720, facingMode: "user" }
          });
          video.srcObject = stream;
          video.play();

          if (typeof Camera !== "undefined" && poseDetector) {
            cameraInstance = new Camera(video, {
              onFrame: async () => {
                if (sessionState.statut === "en_cours") {
                  await poseDetector.send({ image: video });
                }
              },
              width: 1280,
              height: 720
            });
            cameraInstance.start();
          } else {
            // Boucle requestAnimationFrame alternative
            const loop = async () => {
              if (sessionState.statut === "en_cours" && poseDetector) {
                await poseDetector.send({ image: video });
              }
              if (sessionState.statut !== "terminee") {
                requestAnimationFrame(loop);
              }
            };
            requestAnimationFrame(loop);
          }
        } catch (err) {
          alert("Accès caméra refusé ou non disponible. Veuillez autoriser la caméra ou sélectionner une vidéo d'exemple.");
          sessionState.statut = "non_demarre";
        }
      } else {
        // Mode Échantillon vidéo pré-enregistrée
        video.srcObject = null;
        video.src = selectedSampleFile.value || (selectedExercice.value?.video_sample || "/samples/squat.mp4");
        video.loop = true;
        video.muted = true;
        video.play();

        const processVideoFrame = async () => {
          if (sessionState.statut === "en_cours" && poseDetector && !video.paused && !video.ended) {
            await poseDetector.send({ image: video });
          }
          if (sessionState.statut !== "terminee") {
            requestAnimationFrame(processVideoFrame);
          }
        };
        video.onloadeddata = () => {
          requestAnimationFrame(processVideoFrame);
        };
      }
    };

    const mettreEnPause = () => {
      sessionState.statut = "en_pause";
      if (videoElement.value && selectedVideoSource.value !== "webcam") {
        videoElement.value.pause();
      }
    };

    const reprendre = () => {
      sessionState.statut = "en_cours";
      if (videoElement.value && selectedVideoSource.value !== "webcam") {
        videoElement.value.play();
      }
    };

    const terminerSeance = async () => {
      sessionState.statut = "terminee";
      clearInterval(timerInterval);

      // Couper flux caméra (Figure 6, msg 7-8)
      if (videoElement.value && videoElement.value.srcObject) {
        const tracks = videoElement.value.srcObject.getTracks();
        tracks.forEach(t => t.stop());
        videoElement.value.srcObject = null;
      }
      if (cameraInstance) {
        try { cameraInstance.stop(); } catch (e) {}
      }

      // Clôture côté serveur : PUT /seances/{id} (Figure 6, msg 9-15)
      try {
        const payload = {
          duree_secondes: sessionState.dureeSecondes,
          total_repetitions: sessionState.totalRepetitions,
          repetitions: sessionState.historiqueRepetitions,
          retours_correction: sessionState.historiqueCorrections
        };

        const res = await fetch(`${API_BASE}/seances/${sessionState.idSeance}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        recapitulatifSeance.value = data.recapitulatif;

        if (data.objectif_atteint) {
          // Notification atteinte objectif (Service de notification externe)
          setTimeout(() => {
            alert(`🏆 Félicitations ! Votre objectif a été validé ! ${data.notification?.message || ""}`);
            loadNotifications();
          }, 600);
        }
      } catch (e) {
        console.error("Erreur clôture séance:", e);
        recapitulatifSeance.value = {
          exercice_nom: selectedExercice.value?.nom,
          duree_secondes: sessionState.dureeSecondes,
          total_repetitions: sessionState.totalRepetitions,
          calories_estimees: sessionState.calories,
          repetitions: sessionState.historiqueRepetitions,
          retours_correction: sessionState.historiqueCorrections
        };
      }

      loadHistorique(); loadPlanning();
      loadObjectifs();
    };

    // --- ACTIONS MODALES & AUTHENTIFICATION ---
    const switchUserFast = (role, id, nom, prenom, email) => {
      currentUser.value = {
        id,
        nom,
        prenom,
        email,
        role,
        poids: 74.0,
        taille: 178.0,
        niveau: "Intermédiaire"
      };
      loadObjectifs();
      loadHistorique(); loadPlanning();
      loadNotifications();
      if (role === "administrateur") loadAdminData();
    };

    const ouvrirAuth = (mode = "login", reason = "") => {
      authForm.mode = mode;
      authPromptReason.value = reason;
      authMessage.value = "";
      showPassword.value = false;
      isAuthModalOpen.value = true;
    };

    const fermerAuth = () => {
      isAuthModalOpen.value = false;
      authMessage.value = "";
    };

    const handleAuth = async () => {
      authMessage.value = "";
      authMessageType.value = "error";
      const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(authForm.email);
      if (!emailOk) { authMessage.value = "Veuillez saisir une adresse e-mail valide."; return; }
      if (!authForm.mot_de_passe || authForm.mot_de_passe.length < 6) {
        authMessage.value = "Le mot de passe doit contenir au moins 6 caractères."; return;
      }
      if (authForm.mode === "register" && (!authForm.nom || !authForm.prenom)) {
        authMessage.value = "Veuillez renseigner votre nom et votre prénom."; return;
      }

      const endpoint = authForm.mode === "login" ? "/auth/login" : "/auth/register";
      try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(authForm)
        });
        const data = await res.json();
        if (!res.ok) {
          authMessage.value = data.detail || "Erreur d'authentification.";
          return;
        }
        currentUser.value = data.user;
        const veutSEntrainer = !!authPromptReason.value;
        fermerAuth();
        authForm.mot_de_passe = "";
        if (veutSEntrainer && selectedExercice.value) activeView.value = "workout";
        loadObjectifs();
        loadHistorique(); loadPlanning();
        loadNotifications();
        if (data.user.role === "administrateur") loadAdminData();
      } catch (e) {
        authMessage.value = "Impossible de joindre le serveur. Vérifiez qu'il est bien lancé.";
      }
    };

    const seDeconnecter = () => {
      currentUser.value = {
        id: 0,
        nom: "Visiteur",
        prenom: "Anonyme",
        email: "visiteur@fitness.ai",
        role: "visiteur",
        poids: 70,
        taille: 175,
        niveau: "Débutant"
      };
      planifications.value = [];
      activeView.value = "catalogue";
    };

    const handleCreerObjectif = async () => {
      try {
        const res = await fetch(`${API_BASE}/objectifs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sportif_id: currentUser.value.id,
            exercice_id: nouvelObjectif.exercice_id,
            repetitions_cible: nouvelObjectif.repetitions_cible,
            periode: nouvelObjectif.periode,
            date_limite: nouvelObjectif.date_limite || "2026-12-31"
          })
        });
        if (res.ok) {
          isNewObjModalOpen.value = false;
          loadObjectifs();
        }
      } catch (e) {
        console.error("Erreur création objectif:", e);
      }
    };

    const handleCreerOuModifierExercice = async () => {
      try {
        const method = nouvelExercice.id ? "PUT" : "POST";
        const url = nouvelExercice.id ? `${API_BASE}/exercices/${nouvelExercice.id}` : `${API_BASE}/exercices`;
        const res = await fetch(url, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(nouvelExercice)
        });
        if (res.ok) {
          isNewExoModalOpen.value = false;
          loadCatalogue();
        }
      } catch (e) {
        console.error("Erreur exercice admin:", e);
      }
    };

    const ouvrirModifExercice = (exo) => {
      nouvelExercice.id = exo.id;
      nouvelExercice.nom = exo.nom;
      nouvelExercice.description = exo.description;
      nouvelExercice.groupe_musculaire = exo.groupe_musculaire;
      nouvelExercice.difficulte = exo.difficulte;
      nouvelExercice.video_sample = exo.video_sample || "";
      nouvelExercice.regle = { ...(exo.regle || {
        articulation_cle: "genou",
        angle_haut: 160.0,
        angle_bas: 90.0,
        tolerance: 10.0,
        duree_min_repetition: 600
      })};
      isNewExoModalOpen.value = true;
    };

    const supprimerExercice = async (id) => {
      if (!confirm("Voulez-vous supprimer cet exercice et ses règles de comptage ?")) return;
      try {
        await fetch(`${API_BASE}/exercices/${id}`, { method: "DELETE" });
        loadCatalogue();
      } catch (e) {
        console.error("Erreur suppression:", e);
      }
    };

    const voirDetailSeance = async (seanceId) => {
      try {
        const res = await fetch(`${API_BASE}/seances/${seanceId}`);
        detailSeance.value = await res.json();
        isDetailModalOpen.value = true;
      } catch (e) {
        console.error("Erreur détail séance:", e);
      }
    };

    const partagerResultat = () => {
      isShareModalOpen.value = true;
    };

    const copierTextePartage = () => {
      const s = recapitulatifSeance.value || sessionState;
      const exo = s.exercice_nom || selectedExercice.value?.nom;
      const reps = s.total_repetitions;
      const texte = `💪 Séance terminée sur AI Fitness Counter ! J'ai réalisé ${reps} répétitions de ${exo} en ${formatChrono(s.duree_secondes)} (${s.calories_estimees || sessionState.calories} kcal brûlées). Posture validée par vision par ordinateur ! 🚀`;
      navigator.clipboard.writeText(texte);
      alert("Résultat copié dans le presse-papier ! Vous pouvez le coller sur vos réseaux sociaux.");
    };

    // Formatage temps
    const formatChrono = (sec) => {
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    };


    // ======================================================================
    // VIDÉOS D'EXERCICES (aperçu catalogue, démonstration, gestion admin)
    // ======================================================================
    const ORIGIN = API_BASE.replace(/\/api$/, "");
    const mediaUrl = (p) => (!p ? "" : /^https?:/.test(p) ? p : ORIGIN + encodeURI(p));
    const authHeaders = () => ({
      Authorization: `Bearer token-${currentUser.value.id}-${currentUser.value.role}`
    });

    const videos = ref([]);
    const isVideoModalOpen = ref(false);
    const videoExo = ref(null);
    const videoForm = reactive({ titre: "", fichier: null });
    const videoMessage = ref("");
    const videoEnvoi = ref(false);
    const champVideo = ref(null);

    const loadVideos = async () => {
      try {
        const res = await fetch(`${API_BASE}/videos`);
        const data = await res.json();
        videos.value = data.map(v => ({ ...v, url: ORIGIN + v.url }));
      } catch (e) {
        console.error("Erreur chargement vidéos:", e);
      }
    };

    const videosDe = (exo) => videos.value.filter(v => v.exercice_id === exo.id);
    // Vidéo ajoutée par l'admin en priorité, sinon la vidéo de test de l'exercice
    const videoPour = (exo) => {
      if (!exo) return "";
      const v = videosDe(exo)[0];
      return v ? v.url : mediaUrl(exo.video_sample);
    };

    const playPreview = (e) => {
      const v = e.currentTarget.querySelector("video");
      if (v) { v.currentTime = 0.8; v.play().catch(() => {}); }
    };
    const stopPreview = (e) => {
      const v = e.currentTarget.querySelector("video");
      if (v) v.pause();
    };

    const ouvrirVideosAdmin = (exo) => {
      videoExo.value = exo;
      videoForm.titre = "";
      videoForm.fichier = null;
      videoMessage.value = "";
      isVideoModalOpen.value = true;
    };
    const onFichierVideo = (e) => { videoForm.fichier = e.target.files[0] || null; };

    const envoyerVideo = async () => {
      videoMessage.value = "";
      if (!videoForm.fichier) { videoMessage.value = "Choisissez d'abord un fichier vidéo."; return; }
      if (videoForm.fichier.size > 100 * 1024 * 1024) { videoMessage.value = "Vidéo trop lourde (100 Mo maximum)."; return; }
      const fd = new FormData();
      fd.append("exercice_id", videoExo.value.id);
      fd.append("titre", videoForm.titre);
      fd.append("fichier", videoForm.fichier);
      videoEnvoi.value = true;
      try {
        const res = await fetch(`${API_BASE}/videos`, { method: "POST", headers: authHeaders(), body: fd });
        const data = await res.json();
        if (!res.ok) { videoMessage.value = data.detail || "Échec de l'envoi."; return; }
        videoForm.titre = ""; videoForm.fichier = null;
        if (champVideo.value) champVideo.value.value = "";
        await loadVideos();
      } catch (e) {
        videoMessage.value = "Impossible de joindre le serveur.";
      } finally {
        videoEnvoi.value = false;
      }
    };

    const supprimerVideo = async (v) => {
      if (!confirm("Supprimer cette vidéo définitivement ?")) return;
      try {
        const res = await fetch(`${API_BASE}/videos/${v.id}`, { method: "DELETE", headers: authHeaders() });
        if (!res.ok) { videoMessage.value = (await res.json()).detail || "Suppression impossible."; return; }
        await loadVideos();
      } catch (e) { videoMessage.value = "Impossible de joindre le serveur."; }
    };

    // ======================================================================
    // CALENDRIER D'ENTRAÎNEMENT
    // ======================================================================
    const NOMS_MOIS = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"];
    const joursSemaine = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"];
    const cleDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

    const maintenant = new Date();
    const calMois = reactive({ annee: maintenant.getFullYear(), mois: maintenant.getMonth() });
    const jourSelectionne = ref(cleDate(maintenant));
    const planifications = ref([]);
    const nouvellePlanif = reactive({ exercice_id: 1, heure: "18:00", note: "" });
    const planifMessage = ref("");

    const nomMois = computed(() => NOMS_MOIS[calMois.mois]);

    const loadPlanning = async () => {
      if (!currentUser.value || currentUser.value.role === "visiteur") { planifications.value = []; return; }
      try {
        const res = await fetch(`${API_BASE}/planning`, { headers: authHeaders() });
        planifications.value = res.ok ? await res.json() : [];
      } catch (e) { console.error("Erreur chargement planning:", e); }
    };

    const seancesParJour = computed(() => {
      const m = {};
      (historiqueSeances.value || []).forEach(s => {
        const k = String(s.date_debut).slice(0, 10);
        (m[k] = m[k] || []).push(s);
      });
      return m;
    });
    const planifsParJour = computed(() => {
      const m = {};
      planifications.value.forEach(p => { (m[p.date_prevue] = m[p.date_prevue] || []).push(p); });
      return m;
    });

    const joursCalendrier = computed(() => {
      const premier = new Date(calMois.annee, calMois.mois, 1);
      const decalage = (premier.getDay() + 6) % 7;                 // semaine commençant le lundi
      const nbJours = new Date(calMois.annee, calMois.mois + 1, 0).getDate();
      const auj = cleDate(new Date());
      const cases = Array(decalage).fill(null);
      for (let jour = 1; jour <= nbJours; jour++) {
        const cle = cleDate(new Date(calMois.annee, calMois.mois, jour));
        cases.push({
          jour, cle, aujourdhui: cle === auj,
          seances: (seancesParJour.value[cle] || []).length,
          prevues: (planifsParJour.value[cle] || []).filter(p => p.statut !== "faite").length
        });
      }
      return cases;
    });

    const statsMois = computed(() => {
      const prefixe = `${calMois.annee}-${String(calMois.mois + 1).padStart(2, "0")}`;
      let seances = 0, reps = 0; const jours = new Set();
      (historiqueSeances.value || []).forEach(s => {
        if (String(s.date_debut).startsWith(prefixe)) {
          seances++; reps += s.total_repetitions || 0; jours.add(String(s.date_debut).slice(0, 10));
        }
      });
      const auj = cleDate(new Date());
      const prevues = planifications.value.filter(p => p.statut !== "faite" && p.date_prevue >= auj).length;
      return { seances, reps, jours: jours.size, prevues };
    });

    const detailJour = computed(() => ({
      seances: seancesParJour.value[jourSelectionne.value] || [],
      planifs: planifsParJour.value[jourSelectionne.value] || []
    }));
    const libelleJour = computed(() => {
      const [a, m, d] = jourSelectionne.value.split("-").map(Number);
      const t = new Date(a, m - 1, d).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
      return t.charAt(0).toUpperCase() + t.slice(1);
    });
    const jourSelectionneCourt = computed(() => {
      const [a, m, d] = jourSelectionne.value.split("-").map(Number);
      return new Date(a, m - 1, d).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
    });

    const moisPrecedent = () => { if (calMois.mois === 0) { calMois.mois = 11; calMois.annee--; } else calMois.mois--; };
    const moisSuivant = () => { if (calMois.mois === 11) { calMois.mois = 0; calMois.annee++; } else calMois.mois++; };
    const aujourdhui = () => {
      const n = new Date();
      calMois.annee = n.getFullYear(); calMois.mois = n.getMonth(); jourSelectionne.value = cleDate(n);
    };

    const ajouterPlanif = async () => {
      planifMessage.value = "";
      try {
        const res = await fetch(`${API_BASE}/planning`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({
            exercice_id: nouvellePlanif.exercice_id, date_prevue: jourSelectionne.value,
            heure: nouvellePlanif.heure || "18:00", note: nouvellePlanif.note
          })
        });
        const data = await res.json();
        if (!res.ok) { planifMessage.value = data.detail || "Ajout impossible."; return; }
        nouvellePlanif.note = "";
        await loadPlanning();
      } catch (e) { planifMessage.value = "Impossible de joindre le serveur."; }
    };

    const basculerPlanif = async (p) => {
      const statut = p.statut === "faite" ? "prevue" : "faite";
      await fetch(`${API_BASE}/planning/${p.id}`, {
        method: "PUT", headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ statut })
      });
      await loadPlanning();
    };

    const supprimerPlanif = async (p) => {
      await fetch(`${API_BASE}/planning/${p.id}`, { method: "DELETE", headers: authHeaders() });
      await loadPlanning();
    };

    const demarrerPlanif = (p) => {
      const exo = catalogue.value.find(e => e.id === p.exercice_id);
      if (exo) choisirExercice(exo);
    };

    onMounted(() => {
      loadVideos();
      loadCatalogue();
      loadSamples();
      loadObjectifs();
      loadHistorique(); loadPlanning();
      loadNotifications();
    });

    onBeforeUnmount(() => {
      if (timerInterval) clearInterval(timerInterval);
    });

    return {
      videos, isVideoModalOpen, videoExo, videoForm, videoMessage, videoEnvoi, champVideo,
      videosDe, videoPour, playPreview, stopPreview, ouvrirVideosAdmin, onFichierVideo, envoyerVideo, supprimerVideo,
      calMois, nomMois, joursSemaine, joursCalendrier, jourSelectionne, statsMois, detailJour, libelleJour,
      jourSelectionneCourt, planifications, nouvellePlanif, planifMessage,
      moisPrecedent, moisSuivant, aujourdhui, ajouterPlanif, basculerPlanif, supprimerPlanif, demarrerPlanif,
      activeView,
      currentUser,
      catalogue,
      selectedExercice,
      selectedVideoSource,
      sampleVideos,
      selectedSampleFile,
      sessionState,
      recapitulatifSeance,
      detailSeance,
      objectifs,
      historiqueSeances,
      notifications,
      isNotifOpen,
      adminUsers,
      adminStats,
      isAuthModalOpen,
      isProfileModalOpen,
      isShareModalOpen,
      isDetailModalOpen,
      isNewExoModalOpen,
      isNewObjModalOpen,
      authForm,
      authPromptReason,
      showPassword,
      authMessage,
      authMessageType,
      ouvrirAuth,
      fermerAuth,
      nouvelObjectif,
      nouvelExercice,
      videoElement,
      canvasElement,
      choisirExercice,
      lancerSeance,
      mettreEnPause,
      reprendre,
      terminerSeance,
      switchUserFast,
      handleAuth,
      seDeconnecter,
      handleCreerObjectif,
      handleCreerOuModifierExercice,
      ouvrirModifExercice,
      supprimerExercice,
      voirDetailSeance,
      partagerResultat,
      copierTextePartage,
      formatChrono
    };
  }
});

app.mount("#app");