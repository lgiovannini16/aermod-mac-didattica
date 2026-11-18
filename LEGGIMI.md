# Preparare AERMOD per Mac dal browser di Windows

Questo kit prepara due compilazioni native di AERMOD, AERMAP e AERMET con
GitHub Actions: Intel e Apple Silicon. Non contiene eseguibili gia' compilati.

**Stato:** sintassi e componenti Python verificati su Linux; compilazione,
collegamento e sample run su macOS devono ancora essere eseguiti su GitHub.
La prima esecuzione puo' richiedere aggiustamenti. Nessun repository e' stato
creato e nessuna compilazione online e' stata avviata per conto dell'utente.

## 1. Controllo preliminare

Chiedere ai tre studenti il processore e la versione di macOS, visibili in
menu Apple > Informazioni su questo Mac. Il workflow iniziale usa macOS 15
come versione minima dichiarata; non promette compatibilita' con macOS 14 o
precedenti. Per studenti con sistemi precedenti occorre adeguare runner,
toolchain e target, e verificare nuovamente il pacchetto.

Accertarsi che le versioni dei tre programmi su Windows coincidano con quelle
scaricate dalla procedura. Lo script esterno usa i sorgenti EPA disponibili al
momento dell'esecuzione: la versione non e' bloccata dal solo nome del workflow.

## 2. Creazione del repository (tutto dal browser)

1. Accedere a https://github.com/ e creare un repository, per esempio
   `aermod-mac-didattica`. Scegliere **Public** per utilizzare gratuitamente i
   runner standard macOS. Il codice caricato sara' pubblico. Non caricare dati
   personali o altri documenti del corso: il kit e il sample EPA sono sufficienti.
   Se si preferisce Private, controllare i minuti inclusi e le impostazioni di costo.
2. Con **Add file > Upload files**, caricare nella radice `LEGGIMI.md`,
   `GUIDA-STUDENTI.txt` e la cartella `scripts` completa. Salvare con **Commit changes**.
3. Con **Add file > Create new file**, inserire esattamente questo nome:
   `.github/workflows/build-macos.yml`.
4. Aprire sul proprio PC `github-workflows/build-macos.yml` con un editor di testo,
   copiare tutto il contenuto nel nuovo file GitHub e salvare con **Commit changes**.
   La cartella github-workflows nel kit serve soltanto a rendere il file facile da
   trovare su Windows; il percorso in GitHub deve iniziare con `.github/workflows/`.

## 3. Avvio e download

1. Aprire la scheda **Actions** del repository.
2. Selezionare **AERMOD per Mac**, poi **Run workflow**.
3. Per la prima prova lasciare `build_ref = main` e l'URL del sample EPA proposto.
   Il valore `build_ref` identifica la revisione dello script del progetto
   indipendente PyAERMOD, non la versione EPA del modello.
4. Attendere la conclusione dei due lavori. Se un lavoro fallisce, aprire il primo
   passo rosso e scaricare `Diagnostica-Intel` o `Diagnostica-AppleSilicon`.
   Non distribuire binari di una compilazione non verificata.
5. Con i lavori riusciti, aprire l'esecuzione e scendere ad **Artifacts**.
   Scaricare `AERMOD-Mac-Intel` e/o `AERMOD-Mac-AppleSilicon`.
   GitHub puo' aggiungere uno ZIP esterno: al suo interno c'e' lo ZIP del pacchetto
   da conservare e distribuire. Il suo formato conserva i permessi eseguibili.
6. Gli artifact scadono dopo 30 giorni: salvare i pacchetti finali sul proprio PC.

## 4. Cosa fa la procedura

- Esegue sui Mac GitHub lo script `scripts/build_aermod.sh all` di PyAERMOD,
  che documenta il download dei sorgenti EPA e la compilazione dei tre programmi.
- Copia ricorsivamente le librerie non di sistema nelle cartelle del pacchetto,
  riscrive i collegamenti e applica una firma locale ad hoc.
- Scarica il sample EPA e registra URL e checksum. Converte i percorsi negli input
  da Windows a macOS e registra gli adattamenti, senza modificare i parametri fisici.
- Rimuove gli output principali preesistenti, esegue AERMAP, i due stadi AERMET
  e AERMOD. Verifica la produzione degli output principali, il messaggio finale
  di AERMOD e il riepilogo degli errori fatali. Il sample EPA documenta che
  `aermap.src` puo' essere vuoto: questo caso specifico e' consentito.
- Ripete l'esecuzione con le librerie GCC del runner temporaneamente nascoste,
  per rilevare dipendenze accidentali dal compilatore installato sul Mac GitHub.
- Confronta gli output con i file _ORG inclusi e conserva le differenze testuali.
  Il confronto non certifica automaticamente equivalenza numerica.

## 5. Revisione prima della lezione

Controllare `reports/ESITO.txt`, i log dei quattro passaggi, i warning e i file
`.diff`. Differenze di timestamp, percorsi, intestazioni o ultima cifra numerica
possono essere attese; differenze nei risultati fisici richiedono approfondimento.
Confrontare le concentrazioni riassuntive con il proprio run Windows, usando
le stesse versioni e gli stessi input. Un workflow verde certifica i controlli
tecnici indicati, non l'equivalenza di tutti i risultati scientifici.

Fare aprire il pacchetto almeno a uno studente per ciascuna architettura presente
in classe: questa prova verifica anche permessi, autorizzazioni macOS e portabilita'.
La firma ad hoc non elimina le eventuali richieste di Gatekeeper.

In `diagnostics/pyaermod-commit.txt` viene registrato il commit usato. Dopo la
prima compilazione riuscita, riutilizzare quel codice come `build_ref` per fissare
lo script. I sorgenti EPA restano scaricati dal sito ufficiale: conservare il
pacchetto riuscito, la diagnostica e i checksum per riprodurre la lezione.

## Possibili ostacoli della prima compilazione

Lo script PyAERMOD puo' cambiare; un download EPA puo' essere temporaneamente
bloccato; la toolchain Homebrew puo' richiedere correzioni; il sample puo' essere
aggiornato. Il kit interrompe l'esecuzione invece di presentare come pronto un
pacchetto che non supera le verifiche. In caso di errore, conservare il log del
passaggio rosso: permette di correggere precisamente il problema.

## Fonti

- Runner GitHub: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- Artifact: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts
- Compilazione PyAERMOD: https://atmmod.github.io/pyaermod/teaching/student-guide/setup/
- Sorgenti e versioni EPA: https://www.epa.gov/scram/air-quality-dispersion-modeling-preferred-and-recommended-models
- Sample: https://gaftp.epa.gov/air/aqmg/SCRAM/models/preferred/aermod/AERMOD_Sample_Run_Instructions.pdf

La procedura usa un progetto indipendente per compilare i sorgenti EPA. Non
richiede installare l'interfaccia Python di PyAERMOD sui computer degli studenti.
