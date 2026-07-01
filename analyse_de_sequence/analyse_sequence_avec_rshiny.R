# Installation des bibliothèques nécessaires 

library(shiny)
library(bslib)
library(TraMineR)
library(TraMineRextras)
library(WeightedCluster)
library(cluster)
library(seqhandbook)
library(dendextend)
library(RColorBrewer)
library(DT)
library(dplyr)

# ***************************************************************************************************************
# Dictionnaire de traduction en français pour DataTables 

lang_fr <- list(
  processing = "Traitement en cours...",
  search = "Rechercher :",
  lengthMenu = "Afficher _MENU_ éléments",
  info = "_START_ - _END_ / _TOTAL_",
  infoEmpty = "0 - 0 / 0",
  infoFiltered = "(filtré sur _MAX_)",
  loadingRecords = "Chargement en cours...",
  zeroRecords = "Aucun élément à afficher",
  emptyTable = "Aucune donnée disponible dans le tableau",
  paginate = list(
    "first" = "Premier",
    "previous" = "Précédent",
    "next" = "Suivant",
    "last" = "Dernier"
  )
)

# ************************************************************************************************************
# Chargement et Préparation des Données


# jeu de donnée contenant les chaînes de coréférences pour effectuer l'analyse de séquence 

sequences_data <- read.csv(
  "sequences_coreferences_francais.csv",
  header       = TRUE,
  na.strings   = '',
  fill         = TRUE,
  sep          = ',',
  fileEncoding = "UTF-8"
)


# jeu de donnée contenant à la fois les annotations du corpus et les annotations de coréférences

comparaison_data <- read.csv(
  "comparaison_coref_temp.csv",
  header       = TRUE,
  sep          = ',',
  fileEncoding = "UTF-8"
)

# Reconstruction mention par mention 

df_valid <- comparaison_data %>% filter(mention_id != "Non applicable" & !is.na(mention_id))
chaines_uniques <- df_valid %>% select(doc, mention_id, chaine_complete) %>% distinct()

xml_reconstruit_list <- lapply(1:nrow(chaines_uniques), function(i) {
  current_doc    <- chaines_uniques$doc[i]
  current_mid    <- chaines_uniques$mention_id[i]
  current_chaine <- chaines_uniques$chaine_complete[i]
  
  heads <- unlist(strsplit(as.character(current_chaine), ",\\s*"))
  df_sub <- df_valid %>% filter(doc == current_doc, mention_id == current_mid)
  ent_list_low <- tolower(trimws(as.character(df_sub$entité)))
  
  trouver_index <- function(h) {
    h_low <- tolower(trimws(h))
    exact_idx <- which(ent_list_low == h_low)
    if (length(exact_idx) > 0) return(exact_idx[1])
    h_escaped <- gsub("([.|()\\^{}+$*?]|\\[|\\])", "\\\\\\1", h_low)
    pattern <- paste0("\\b", h_escaped, "\\b")
    match_idx <- which(sapply(ent_list_low, function(ent_low) {
      ent_escaped <- gsub("([.|()\\^{}+$*?]|\\[|\\])", "\\\\\\1", ent_low)
      pattern_ent <- paste0("\\b", ent_escaped, "\\b")
      grepl(pattern, ent_low, perl=TRUE) || grepl(pattern_ent, h_low, perl=TRUE)
    }))
    if (length(match_idx) > 0) return(match_idx[1])
    fallback_idx <- which(sapply(ent_list_low, function(ent_low) {
      grepl(h_low, ent_low, fixed = TRUE) || grepl(ent_low, h_low, fixed = TRUE)
    }))
    if (length(fallback_idx) > 0) return(fallback_idx[1])
    return(NA)
  }
  
  indices  <- sapply(heads, trouver_index)
  xml_types <- sapply(1:length(heads), function(idx) {
    if (!is.na(indices[idx])) as.character(df_sub$type_temporalite[indices[idx]]) else "Non annoté"
  })
  
  valid_idx <- which(xml_types != "Non annoté")
  xml_types_herites <- sapply(seq_along(xml_types), function(j) {
    if (xml_types[j] != "Non annoté") return(xml_types[j])
    if (length(valid_idx) == 0) return("Non annoté")
    left_v <- valid_idx[valid_idx < j]
    if (length(left_v) > 0) return(xml_types[max(left_v)])
    right_v <- valid_idx[valid_idx > j]
    return(xml_types[min(right_v)])
  })
  
  mots_classes <- sapply(1:length(heads), function(idx) {
    if (!is.na(indices[idx])) as.character(df_sub$entité[indices[idx]]) else heads[idx]
  })
  
  data.frame(
    doc = current_doc,
    mention_id = current_mid,
    sequence_XML = paste(xml_types, collapse = " -> "),
    sequence_XML_heritee = paste(xml_types_herites, collapse = " -> "),
    vrais_mots = paste(mots_classes, collapse = ", "),
    stringsAsFactors = FALSE
  )
})

xml_reconstruit <- do.call(rbind, xml_reconstruit_list)

# création d'un dictionnaire de couleurs pour l'attribution des couleurs aux mots

couleurs_dico <- c(
  "SNdef"      = "#FFFF99", "SNind"      = "#fb8072",
  "SNdem"      = "#80b1d3", "SN\u2205"   = "#579C91",
  "SNnum"      = "#3F84DE", "Poss"       = "#C45C47",
  "Pro"        = "#7B1FA2", "Np"         = "#FDC086",
  "Sujet_zero" = "#96B0B7", "SNposs"     = "#FF0000",
  "Autre"      = "#b3de69"
)

# Détection dynamique de l'alphabet

etats_trouves  <- seqstatl(sequences_data[, 7:24])

# Extraire uniquement les couleurs dans l'ordre de l'alphabet trouvé par R
cpal_dynamique <- unname(couleurs_dico[etats_trouves])

# Création de l'objet Séquence
coref_chaines.seq <- seqdef(
  sequences_data[, 7:24], alphabet = etats_trouves, states = etats_trouves,
  cpal = cpal_dynamique, with.missing = FALSE
)

# On selectionne des colonnes avec les informations que l'on veut et on choisi le format des séquences 
#SPS est le format qui permet d'avoir l'état et sa durée 

sequences_SPS <- seqformat(sequences_data, 
                           7:24, from = "STS", 
                           to = "SPS", 
                           compress = TRUE, 
                           with.missing = FALSE)


#ici on stocke les sequences au format SPS pour les recuperer 

sequences_data$sequences_SPS <- sequences_SPS


# Calcul des distances et Clustering

matrice_sub  <- seqsubm(coref_chaines.seq, method = "TRATE")

# On compare les  chaînes entre elles pour voir lesquelles se ressemblent

distances_om <- seqdist(coref_chaines.seq, method = "OM", indel = 1, sm = matrice_sub)

# On regroupe les chaînes qui ont des trajectoires similaires

arbre_ward   <- agnes(as.dist(distances_om), diss = TRUE, method = "ward")
ordre_random <- cmdscale(as.dist(distances_om), k = 1)

hauteurs         <- sort(arbre_ward$height, decreasing = TRUE)[1:15]
sauts            <- diff(hauteurs)
grands_sauts_idx <- order(abs(sauts), decreasing = TRUE)[1:4]
couleurs_sauts   <- c("#E74C3C", "#FFFF00", "#8E44AD", "#27AE60")

 

# On utilise match() pour convertir chaque état en son index dans l'alphabet.

seq_heatmap_custom <- function(seqdata, tree, with.missing = FALSE, ...) {
  if (!inherits(tree, "dendrogram")) tree <- as.dendrogram(tree)
  alphabet <- attr(seqdata, "alphabet")
  mat_char <- as.matrix(seqdata)
  mat_char[mat_char == "%"] <- NA
  mat <- matrix(
    match(mat_char, alphabet),
    nrow = nrow(mat_char),
    ncol = ncol(mat_char)
  )
  col <- attr(seqdata, "cpal")
  if (with.missing) col <- c(col, attr(seqdata, "missing.color"))
  heatmap(mat, Rowv = tree, Colv = NA, na.rm = FALSE, col = col, scale = "none", labRow = NA, ...)
}

# ******************************************************************************************************************************************
#  boutons de téléchargement 

boutons_export <- function(id_prefixe) {
  div(
    style = "display:flex; gap:8px; margin-top:8px; flex-wrap:wrap;",
    downloadButton(paste0("dl_", id_prefixe, "_png"), "\u2b07 PNG", style = "font-size:0.8em; padding:4px 10px;"),
    downloadButton(paste0("dl_", id_prefixe, "_jpg"), "\u2b07 JPG", style = "font-size:0.8em; padding:4px 10px;"),
    downloadButton(paste0("dl_", id_prefixe, "_pdf"), "\u2b07 PDF", style = "font-size:0.8em; padding:4px 10px;")
  )
}

# ***********************************************************************************************************************
# Interface Utilisateur (UI)

ui <- tagList(
  
  # CSS global (titre au-dessus + charte de couleurs)
  
  tags$head(tags$style(HTML("

    /* Bandeau supérieur : grand titre */
    .app-header {
      background: linear-gradient(90deg, #1B3A5C 0%, #2E86AB 100%);
      padding: 18px 32px 14px 32px;
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .app-header .app-title {
      color: #FFFFFF;
      font-size: 1.55rem;
      font-weight: 700;
      letter-spacing: 0.3px;
      margin: 0;
      line-height: 1.2;
    }
    .app-header .app-subtitle {
      color: #A8D8EA;
      font-size: 0.82rem;
      margin: 2px 0 0 0;
    }
    .app-header .app-icon {
      font-size: 2rem;
      color: #F0A500;
    }

    /* Navbar : menus uniquement, sans titre */
    .navbar-brand { display: none !important; }
    .navbar {
      background-color: #1B3A5C !important;
      border-bottom: 3px solid #F0A500;
      padding: 0 16px;
    }
    .navbar .nav-link {
      color: #C8DCE8 !important;
      font-weight: 500;
      font-size: 0.9rem;
      padding: 12px 16px !important;
      border-bottom: 3px solid transparent;
      transition: all .15s;
    }
    .navbar .nav-link:hover {
      color: #FFFFFF !important;
      border-bottom-color: #F0A500;
    }
    .navbar .nav-link.active {
      color: #FFFFFF !important;
      border-bottom: 3px solid #F0A500 !important;
      background: rgba(255,255,255,0.08) !important;
    }

    /* card_header : couleur accent */
    .card-header {
      background-color: #1B3A5C !important;
      color: #FFFFFF !important;
      font-weight: 600;
      font-size: 0.92rem;
      border-bottom: 2px solid #F0A500;
      padding: 10px 16px;
    }

    /* Sous-onglets navset_tab */
    .nav-tabs .nav-link {
      color: #2E86AB !important;
      font-weight: 500;
    }
    .nav-tabs .nav-link.active {
      color: #1B3A5C !important;
      border-top: 3px solid #F0A500 !important;
      font-weight: 700;
    }

    /* Titres h5/h6 dans les sidebars */
    .sidebar h5, .bslib-sidebar-layout > .sidebar h5 {
      color: #1B3A5C;
      font-weight: 700;
      font-size: 1rem;
      border-left: 4px solid #F0A500;
      padding-left: 8px;
      margin-bottom: 10px;
    }
    .sidebar h6, .bslib-sidebar-layout > .sidebar h6 {
      color: #2E86AB;
      font-weight: 600;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-top: 8px;
    }

    /* Boutons de téléchargement */
    .btn-dl {
      background-color: #2E86AB;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 0.8em;
      padding: 4px 12px;
      transition: background .15s;
    }
    .btn-dl:hover { background-color: #1B3A5C; color: #F0A500; }
    a.btn.shiny-download-link {
      background-color: #2E86AB !important;
      color: #fff !important;
      border: none !important;
      font-size: 0.8em;
      padding: 4px 12px;
      border-radius: 4px;
      transition: background .15s;
    }
    a.btn.shiny-download-link:hover {
      background-color: #1B3A5C !important;
      color: #F0A500 !important;
    }

    /* value_box override */
    .value-box-title { font-weight: 600 !important; }

    /* Fond général */
    body { background-color: #F4F7FA !important; }
    .card { border: 1px solid #D9E4EE; }

  "))),
  
  # Bandeau titre au-dessus de la navbar 
  
  div(class = "app-header",
      span(class = "app-icon", icon("")),
      div(
        p(class = "app-title",  "Analyse de Séquence appliquée aux chaînes de coréférences"),
        p(class = "app-subtitle", "Corpus : E3C ")
      )
  ),
  
  # Navbar (menus uniquement) 
  page_navbar(
    title  = "",
    theme  = bs_theme(bootswatch = "flatly", base_font = font_google("Inter")),
    window_title = "Analyse de Séquences — Coréférence",
    
    # Onglet 1 : Vue d'ensemble 
    nav_panel(
      title = "Vue d'ensemble",
      icon  = icon("table"),
      navset_tab(
        nav_panel(
          title = "\U0001f4cb Présentation des données",
          card(
            card_header("Jeu de données : sequences_coreferences_francais.csv"),
            p(style = "color:#2C3E50; font-size:0.9em;",
              "Aperçu général du jeu de données utilisé :", br(),
              "Chaque ligne correspond à une chaîne de coréférence.", br(),
              "Les colonnes 7 à 24 contiennent les états de la séquence (nature)."
            ),
            hr(),
            layout_columns(
              col_widths = c(4, 4, 4),
              value_box(title = "Nombre de chaînes", value = textOutput("nb_sequences"), showcase = icon("list"),    theme = "primary"),
              value_box(title = "Colonnes",           value = textOutput("nb_colonnes"),  showcase = icon("columns"), theme = "success"),
              value_box(title = "États distincts",    value = textOutput("nb_etats"),     showcase = icon("palette"), theme = "info")
            ),
            hr(),
            DTOutput("table_sequences_data")
          )
        ),
        nav_panel(
          title = "\U0001f4ca Visualisation Corpus",
          layout_sidebar(
            sidebar = sidebar(
              width = 260,
              h5("Options"),
              radioButtons("vue_plot_type", label = "Graphique :",
                           choices  = c("Trajectoires individuelles" = "iplot",
                                        "Distribution des états"     = "dplot"),
                           selected = "dplot")
            ),
            card(
              full_screen = TRUE,
              card_header(textOutput("vue_plot_title")),
              plotOutput("vue_plot_out", height = "520px"),
              boutons_export("vue_plot")
            )
          )
        )
      )
    ),
    
    # Onglet 2 : Choix et analyse du cluster 
    nav_panel(
      title = "Choix et analyse du cluster",
      icon  = icon("sitemap"),
      layout_sidebar(
        sidebar = sidebar(
          width = 300,
          h5("Configuration"),
          sliderInput("nb_clusters", label = "Nombre de classes (k) :",
                      min = 2, max = 10, value = 4, step = 1),
          hr(),
          h6("Tailles"),
          tableOutput("cluster_sizes"),
          hr(),
          h6("Type de Graphique TraMineR"),
          radioButtons("cluster_plot_type", label = NULL,
                       choices  = c("Distribution des états"    = "dplot",
                                    "Séquences individuelles"   = "iplot",
                                    "Top 10 séquences"          = "fplot",
                                    "Séquences représentatives" = "rplot"),
                       selected = "dplot")
        ),
        navset_tab(
          nav_panel(
            title = "\U0001f333 Dendrogrammes",
            layout_columns(
              col_widths = c(6, 6),
              card(
                full_screen = TRUE,
                card_header("Dendrogramme Ward"),
                plotOutput("dendro_simple", height = "420px"),
                boutons_export("dendro_simple")
              ),
              card(
                full_screen = TRUE,
                card_header("Dendrogramme avec Heatmap"),
                plotOutput("dendro_couleur", height = "420px"),
                boutons_export("dendro_couleur")
              )
            )
          ),
          nav_panel(
            title = "\U0001f4c9 Sauts d'inertie",
            layout_columns(
              col_widths = c(6, 6),
              card(
                full_screen = TRUE,
                card_header("Sauts d'inertie simples"),
                plotOutput("inertie_simple", height = "380px"),
                boutons_export("inertie_simple")
              ),
              card(
                full_screen = TRUE,
                card_header("Coupures identifiées (k optimal)"),
                plotOutput("inertie_couleur", height = "380px"),
                boutons_export("inertie_couleur")
              )
            )
          ),
          nav_panel(
            title = "\U0001f4c8 Description des clusters",
            card_header(textOutput("cluster_card_title")),
            p(style = "font-size:0.85em; color:#2C3E50; padding:6px 2px;",
              textOutput("cluster_plot_desc")),
            plotOutput("cluster_plot_out", height = "750px"),
            boutons_export("cluster_plot")
          )
        )
      )
    ),
    
    # Onglet 3 : Exploration sémantique 
    nav_panel(
      title = "Exploration sémantique",
      icon  = icon("layer-group"),
      navset_card_tab(
        nav_panel(
          title = "Chaînes de coréf vs annotations du corpus",
          card_header("Détail des chaînes et enchaînements par cluster"),
          p(style = "font-size:0.85em; color:#2C3E50;",
            "Ce tableau permet de filtrer par classe pour observer la correspondance entre les chaînes de coréférences et les annotations du corpus."),
          DTOutput("table_exploration_semantique")
        ),
        nav_panel(
          title = "Tableau Filtré",
          card_header("Version nettoyée"),
          p(style = "font-size:0.85em; color:#2C3E50;",
            "Les séquences composées uniquement des 'Non annoté' ont été supprimées de ce tableau."),
          DTOutput("table_exploration_filtree")
        ),
        nav_panel(
          title = "Héritage des Annotations",
          card_header("Propagation Sémantique"),
          p(style = "font-size:0.85em; color:#2C3E50;",
            "Dans ce tableau, les éléments 'Non annoté' ont hérité de la balise (à gauche comme à droite) la plus proche au sein de leur propre chaîne de coréférence."),
          DTOutput("table_exploration_heritage")
        )
      )
    )
  )
)

# *****************************************************************************************************************************************
# Serveur

server <- function(input, output, session) {
  
  clustering_react <- reactive({
    k   <- input$nb_clusters
    cl  <- cutree(arbre_ward, k = k)
    fac <- factor(cl, labels = paste("Classe", 1:k))
    list(cl = cl, fac = fac, k = k)
  })
  
  output$nb_sequences <- renderText({ nrow(sequences_data) })
  output$nb_colonnes  <- renderText({ ncol(sequences_data) })
  output$nb_etats     <- renderText({ length(etats_trouves) })
  
  output$table_sequences_data <- renderDT({
    datatable(
      sequences_data,
      options = list(pageLength = 10, scrollX = TRUE, language = lang_fr),
      rownames = FALSE, filter = "top"
    )
  })
  
  output$vue_plot_title <- renderText({
    if (input$vue_plot_type == "iplot") "Trajectoires individuelles" else "Distribution globale des états"
  })
  
  output$vue_plot_out <- renderPlot({
    if (input$vue_plot_type == "iplot") {
      seqIplot(coref_chaines.seq, main = "Trajectoires", with.legend = "right")
    } else {
      seqdplot(coref_chaines.seq, main = "Proportions", with.legend = "right")
    }
  }, res = 100)
  
  output$dendro_simple <- renderPlot({
    plot(as.dendrogram(arbre_ward), main = "Arbre de Ward", leaflab = "none", xlab = "Séquences", ylab = "Inertie")
  }, res = 100)
  
  output$dendro_couleur <- renderPlot({
    seq_heatmap_custom(coref_chaines.seq, arbre_ward)
  }, res = 100)
  
  output$inertie_simple <- renderPlot({
    plot(sort(arbre_ward$height, decreasing = TRUE)[1:15], type = 's', xlab = "k", ylab = "Inertie", col = "blue", lwd = 2)
  }, res = 100)
  
  output$inertie_couleur <- renderPlot({
    plot(hauteurs, type = 's', xlab = "Nombre de clusters", ylab = "Inertie", col = "steelblue", lwd = 2.5)
    abline(v = grands_sauts_idx, lty = 2, col = adjustcolor(couleurs_sauts, alpha.f = 0.4), lwd = 1.5)
    points(grands_sauts_idx, hauteurs[grands_sauts_idx], pch = 21, cex = 2.5, bg = couleurs_sauts, col = "white")
    text(grands_sauts_idx, hauteurs[grands_sauts_idx], labels = paste0("k = ", grands_sauts_idx), pos = 1, col = couleurs_sauts, font = 2)
  }, res = 100)
  
  output$cluster_card_title <- renderText({
    d <- clustering_react()
    labels <- c(dplot = "Proportions des états", iplot = "Séquences individuelles",
                fplot = "Top 10 fréquences", rplot = "Médoïdes représentatifs")
    paste0(labels[input$cluster_plot_type], " | k = ", d$k, " clusters")
  })
  
  output$cluster_plot_desc <- renderText({
    switch(input$cluster_plot_type,
           dplot = "",
           iplot = "Une ligne par chaîne de coréférence, ordonnées par similarité au sein de chaque classe.",
           fplot = "Les 10 séquences les plus fréquentes dans chaque classe.",
           rplot = "Séquences représentatives (médoïdes) de chaque classe, sélectionnées par distance minimale au centre."
    )
  })
  
  output$cluster_sizes <- renderTable({
    d  <- clustering_react()
    df <- as.data.frame(table(d$fac))
    colnames(df) <- c("Cluster", "n")
    df
  }, striped = TRUE, hover = TRUE, spacing = "xs")
  
  output$cluster_plot_out <- renderPlot({
    d <- clustering_react()
    if (input$cluster_plot_type == "dplot") {
      seqdplot(coref_chaines.seq, group = d$fac, border = TRUE, main = "Profil des classes")
    } else if (input$cluster_plot_type == "iplot") {
      seqiplot(coref_chaines.seq, group = d$fac, sortv = ordre_random, idxs = 0, space = 0, border = NA, yaxis = FALSE)
    } else if (input$cluster_plot_type == "fplot") {
      seqfplot(coref_chaines.seq, group = d$fac, yaxis = FALSE)
    } else if (input$cluster_plot_type == "rplot") {
      seqrplot(coref_chaines.seq, group = d$fac, dist.matrix = distances_om, criterion = "dist")
    }
  }, res = 100, height = 750)
  
  df_base_complet <- reactive({
    d <- clustering_react()
    df_analyse <- sequences_data
    df_analyse$Cluster_Affecte <- d$fac
    df_analyse %>%
      left_join(xml_reconstruit, by = c("doc", "mention_id")) %>%
      select(
        Document            = doc,
        ID_chaine           = mention_id,
        Cluster             = Cluster_Affecte,
        Enchaînement_nature = sequences_SPS,
        Annotation_corpus   = sequence_XML,
        Annotation_héritée  = sequence_XML_heritee,
        Mots_contexte       = vrais_mots
      )
  })
  
  # Tableau 1 : toutes les données 
  output$table_exploration_semantique <- renderDT({
    df_tab1 <- df_base_complet() %>% select(-Annotation_héritée)
    datatable(df_tab1, extensions = 'Buttons',
              options = list(dom = 'Bfrtip',
                             buttons = list(
                               list(extend = 'copy',  text = 'Copier',   exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'csv',   text = 'CSV',      exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'excel', text = 'Excel',    exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'pdf',   text = 'PDF',      exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'print', text = 'Imprimer', exportOptions = list(modifier = list(page = "all")))
                             ),
                             pageLength = 10, scrollX = TRUE,
                             searchCols = list(NULL, NULL, list(search = "Classe 1"), NULL, NULL, NULL),
                             language = lang_fr),
              rownames = FALSE, filter = "top", class = "stripe hover compact")
  }, server = FALSE)
  
  # Tableau 2 : filtrage (Sans les lignes "Non annoté")
  output$table_exploration_filtree <- renderDT({
    df_clean <- df_base_complet() %>%
      filter(!is.na(Annotation_corpus) & !grepl("^(Non annoté(\\s*->\\s*Non annoté)*)$", Annotation_corpus)) %>%
      select(-Annotation_héritée)
    datatable(df_clean, extensions = 'Buttons',
              options = list(dom = 'Bfrtip',
                             buttons = list(
                               list(extend = 'copy',  text = 'Copier',   exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'csv',   text = 'CSV',      exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'excel', text = 'Excel',    exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'pdf',   text = 'PDF',      exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'print', text = 'Imprimer', exportOptions = list(modifier = list(page = "all")))
                             ),
                             pageLength = 10, scrollX = TRUE,
                             searchCols = list(NULL, NULL, list(search = "Classe 1"), NULL, NULL, NULL),
                             language = lang_fr),
              rownames = FALSE, filter = "top", class = "stripe hover compact")
  }, server = FALSE)
  
  # Tableau 3 : héritage des annotations 
  output$table_exploration_heritage <- renderDT({
    df_heritage <- df_base_complet() %>%
      filter(!is.na(Annotation_corpus) & !grepl("^(Non annoté(\\s*->\\s*Non annoté)*)$", Annotation_corpus))
    datatable(df_heritage, extensions = 'Buttons',
              options = list(dom = 'Bfrtip',
                             buttons = list(
                               list(extend = 'copy',  text = 'Copier',   exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'csv',   text = 'CSV',      exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'excel', text = 'Excel',    exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'pdf',   text = 'PDF',      exportOptions = list(modifier = list(page = "all"))),
                               list(extend = 'print', text = 'Imprimer', exportOptions = list(modifier = list(page = "all")))
                             ),
                             pageLength = 10, scrollX = TRUE,
                             searchCols = list(NULL, NULL, list(search = "Classe 1"), NULL, NULL, NULL, NULL),
                             language = lang_fr),
              rownames = FALSE, filter = "top", class = "stripe hover compact")
  }, server = FALSE)
  
  # ********************************************************************************************************************************
  # téléchargement — fonction générique creer_dl
  
  creer_dl <- function(id_prefixe, expr_plot, width = 12, height = 8) {
    for (fmt in c("png", "jpg", "pdf")) {
      local({
        fmt_local     <- fmt
        prefixe_local <- id_prefixe
        output[[paste0("dl_", prefixe_local, "_", fmt_local)]] <- downloadHandler(
          filename = function() {
            paste0(prefixe_local, "_", Sys.Date(), ".", fmt_local)
          },
          content = function(file) {
            if (fmt_local == "png") {
              png(file,  width = width, height = height, units = "in", res = 150)
            } else if (fmt_local == "jpg") {
              jpeg(file, width = width, height = height, units = "in", res = 150, quality = 95)
            } else if (fmt_local == "pdf") {
              pdf(file,  width = width, height = height)
            }
            expr_plot()
            dev.off()
          }
        )
      })
    }
  }
  
  # vue_plot
  creer_dl("vue_plot", function() {
    if (input$vue_plot_type == "iplot") {
      seqIplot(coref_chaines.seq, main = "Trajectoires", with.legend = "right")
    } else {
      seqdplot(coref_chaines.seq, main = "Proportions", with.legend = "right")
    }
  }, width = 14, height = 8)
  
  # dendro_simple
  creer_dl("dendro_simple", function() {
    plot(as.dendrogram(arbre_ward), main = "Arbre de Ward", leaflab = "none", xlab = "Séquences", ylab = "Inertie")
  }, width = 12, height = 8)
  
  # dendro_couleur
  creer_dl("dendro_couleur", function() {
    seq_heatmap_custom(coref_chaines.seq, arbre_ward)
  }, width = 12, height = 10)
  
  # inertie_simple
  creer_dl("inertie_simple", function() {
    plot(sort(arbre_ward$height, decreasing = TRUE)[1:15], type = 's', xlab = "k", ylab = "Inertie", col = "blue", lwd = 2)
  }, width = 10, height = 6)
  
  # inertie_couleur
  creer_dl("inertie_couleur", function() {
    plot(hauteurs, type = 's', xlab = "Nombre de clusters", ylab = "Inertie", col = "steelblue", lwd = 2.5)
    abline(v = grands_sauts_idx, lty = 2, col = adjustcolor(couleurs_sauts, alpha.f = 0.4), lwd = 1.5)
    points(grands_sauts_idx, hauteurs[grands_sauts_idx], pch = 21, cex = 2.5, bg = couleurs_sauts, col = "white")
    text(grands_sauts_idx, hauteurs[grands_sauts_idx], labels = paste0("k = ", grands_sauts_idx), pos = 1, col = couleurs_sauts, font = 2)
  }, width = 10, height = 6)
  
  # cluster_plot
  creer_dl("cluster_plot", function() {
    d <- clustering_react()
    if (input$cluster_plot_type == "dplot") {
      seqdplot(coref_chaines.seq, group = d$fac, border = TRUE, main = "Profil des classes")
    } else if (input$cluster_plot_type == "iplot") {
      seqiplot(coref_chaines.seq, group = d$fac, sortv = ordre_random, idxs = 0, space = 0, border = NA, yaxis = FALSE)
    } else if (input$cluster_plot_type == "fplot") {
      seqfplot(coref_chaines.seq, group = d$fac, yaxis = FALSE)
    } else if (input$cluster_plot_type == "rplot") {
      seqrplot(coref_chaines.seq, group = d$fac, dist.matrix = distances_om, criterion = "dist")
    }
  }, width = 16, height = 12)
  
}

# **********************************************************************************************************************************
## Lancement de l'application

shinyApp(ui = ui, server = server)