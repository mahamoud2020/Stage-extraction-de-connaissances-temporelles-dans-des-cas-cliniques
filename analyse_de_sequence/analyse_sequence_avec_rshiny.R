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

# ************************************************************************************************************
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

sequences_data <- read.csv(
  "sequences_coreferences_francais.csv",
  header       = TRUE,
  na.strings   = '',
  fill         = TRUE,
  sep          = ',',
  fileEncoding = "UTF-8"
)

comparaison_data <- read.csv(
  "comparaison_coref_temp.csv",
  header       = TRUE,
  sep          = ',',
  fileEncoding = "UTF-8"
)

# Reconstruction maillon par maillon avec Priorités

df_valid <- comparaison_data %>% filter(mention_id != "Non applicable" & !is.na(mention_id))
chaines_uniques <- df_valid %>% select(doc, mention_id, chaine_complete) %>% distinct()

xml_reconstruit_list <- lapply(1:nrow(chaines_uniques), function(i) {
  current_doc   <- chaines_uniques$doc[i]
  current_mid   <- chaines_uniques$mention_id[i]
  current_chaine <- chaines_uniques$chaine_complete[i]
  
  heads <- unlist(strsplit(as.character(current_chaine), ",\\s*"))
  df_sub <- df_valid %>% filter(doc == current_doc, mention_id == current_mid)
  ent_list_low <- tolower(trimws(as.character(df_sub$entité)))
  
  trouver_index <- function(h) {
    h_low <- tolower(trimws(h))
    
    # Match 
    exact_idx <- which(ent_list_low == h_low)
    if (length(exact_idx) > 0) return(exact_idx[1])
    
    # Match par mot entier
    
    h_escaped <- gsub("([.|()\\^{}+$*?]|\\[|\\])", "\\\\\\1", h_low)
    pattern <- paste0("\\b", h_escaped, "\\b")
    match_idx <- which(sapply(ent_list_low, function(ent_low) {
      ent_escaped <- gsub("([.|()\\^{}+$*?]|\\[|\\])", "\\\\\\1", ent_low)
      pattern_ent <- paste0("\\b", ent_escaped, "\\b")
      grepl(pattern, ent_low, perl=TRUE) || grepl(pattern_ent, h_low, perl=TRUE)
    }))
    if (length(match_idx) > 0) return(match_idx[1])
    
    # Match partiel simple 
    
    fallback_idx <- which(sapply(ent_list_low, function(ent_low) {
      grepl(h_low, ent_low, fixed = TRUE) || grepl(ent_low, h_low, fixed = TRUE)
    }))
    if (length(fallback_idx) > 0) return(fallback_idx[1])
    
    return(NA) 
  }
  
  indices <- sapply(heads, trouver_index)
  
  xml_types <- sapply(1:length(heads), function(idx) {
    if (!is.na(indices[idx])) as.character(df_sub$type_temporalite[indices[idx]]) else "Non annoté"
  })
  
  # Logique du traitement d'héritage
  
  valid_idx <- which(xml_types != "Non annoté")
  xml_types_herites <- sapply(seq_along(xml_types), function(j) {
    if (xml_types[j] != "Non annoté") {
      return(xml_types[j]) # S'il y a déjà une balise, on la garde
    }
    if (length(valid_idx) == 0) {
      return("Non annoté") # Si la chaîne est 100% vide, on ne peut rien hériter
    }
    # Cherche la balise valide la plus proche à gauche
    
    left_v <- valid_idx[valid_idx < j]
    if (length(left_v) > 0) {
      return(xml_types[max(left_v)])
    } else {
      
      # Sinon, on cherche à droite
      
      right_v <- valid_idx[valid_idx > j]
      return(xml_types[min(right_v)])
    }
  })
  
  
  mots_classes <- sapply(1:length(heads), function(idx) {
    if (!is.na(indices[idx])) as.character(df_sub$entité[indices[idx]]) else heads[idx]
  })
  
  data.frame(
    doc = current_doc,
    mention_id = current_mid,
    sequence_XML = paste(xml_types, collapse = " -> "),
    sequence_XML_heritee = paste(xml_types_herites, collapse = " -> "), # Nouvelle colonne
    vrais_mots = paste(mots_classes, collapse = ", "),
    stringsAsFactors = FALSE
  )
})

xml_reconstruit <- do.call(rbind, xml_reconstruit_list)

couleurs_dico <- c(
  "SNdef"      = "#FFFF99", "SNind"      = "#fb8072",
  "SNdem"      = "#80b1d3", "SN\u2205"   = "#579C91",
  "SNnum"      = "#3F84DE", "Poss"       = "#C45C47",
  "Pro"        = "#7B1FA2", "Np"         = "#FDC086",
  "Sujet_zero" = "#96B0B7", "SNposs"     = "#FF0000",
  "Autre"      = "#b3de69"
)

etats_trouves  <- seqstatl(sequences_data[, 7:24])
cpal_dynamique <- unname(couleurs_dico[etats_trouves])

coref_chaines.seq <- seqdef(
  sequences_data[, 7:24], alphabet = etats_trouves, states = etats_trouves,
  cpal = cpal_dynamique, with.missing = FALSE
)

sequences_SPS <- seqformat(sequences_data, 7:24, from = "STS", to = "SPS", compress = TRUE, with.missing = FALSE)
sequences_data$sequences_SPS <- sequences_SPS

matrice_sub  <- seqsubm(coref_chaines.seq, method = "TRATE")
distances_om <- seqdist(coref_chaines.seq, method = "OM", indel = 1, sm = matrice_sub)

arbre_ward   <- agnes(as.dist(distances_om), diss = TRUE, method = "ward")
ordre_random <- cmdscale(as.dist(distances_om), k = 1)

seq_heatmap_custom <- function(seqdata, tree, with.missing = FALSE, ...) {
  if (!inherits(tree, "dendrogram")) {
    tree <- as.dendrogram(tree)
  }
  mat <- as.matrix(seqdata)
  mat[mat == "%"] <- NA
  mat <- apply(mat, 2, as.numeric)
  col <- attr(seqdata, "cpal")
  if (with.missing) {
    col <- c(col, attr(seqdata, "missing.color"))
  }
  heatmap(mat, Rowv = tree, Colv = NA, na.rm = FALSE, col = col, scale = "none", labRow = NA, ...)
}

# ***********************************************************************************************************************
# Interface Utilisateur (UI)

ui <- page_navbar(
  title = "Analyse de Séquence appliquée aux chaînes de coréférences",
  theme = bs_theme(bootswatch = "flatly", base_font = font_google("Inter")),
  
  # Onglet 1 : Vue d'ensemble
  
  nav_panel(
    title = "Vue d'ensemble",
    icon  = icon("table"),
    navset_tab(
      nav_panel(
        title = " Présentation des données",
        card(
          card_header("Jeu de données : sequences_coreferences_francais.csv"),
          p(style = "color:#555; font-size:0.9em;",
            "Aperçu général du jeu de données utilisé :", br(),
            "Chaque ligne correspond à une chaîne de coréférence",br(),
            "Les colonnes 7 à 24 contiennent les états de la séquence (nature)."
          ),
          hr(),
          layout_columns(
            col_widths = c(4, 4, 4),
            value_box(title = "Nombre de chaînes", value = textOutput("nb_sequences"), showcase = icon("list"), theme = "primary"),
            value_box(title = "Colonnes", value = textOutput("nb_colonnes"), showcase = icon("columns"), theme = "success"),
            value_box(title = "États distincts", value = textOutput("nb_etats"), showcase = icon("palette"), theme = "info")
          ),
          hr(),
          DTOutput("table_sequences_data")
        )
      ),
      nav_panel(
        title = "📊 Visualisation Corpus",
        layout_sidebar(
          sidebar = sidebar(
            width = 260, h5("Options"),
            radioButtons("vue_plot_type", label = "Graphique :",
                         choices = c("Trajectoires individuelles" = "iplot", "Distribution des états" = "dplot"), selected = "dplot")
          ),
          card(
            full_screen = TRUE,
            card_header(textOutput("vue_plot_title")),
            plotOutput("vue_plot_out", height = "520px")
          )
        )
      )
    )
  ),
  
  # Onglet 2 : Choix du cluster 
  
  nav_panel(
    title = "Choix et analyse du cluster",
    icon  = icon("sitemap"),
    layout_sidebar(
      sidebar = sidebar(
        width = 300,
        h5("Configuration"),
        sliderInput("nb_clusters", label = "Nombre de classes (k) :", min = 2, max = 10, value = 4, step = 1),
        hr(),
        h6("Tailles"),
        tableOutput("cluster_sizes"),
        hr(),
        h6("Type de Graphique TraMineR"),
        radioButtons("cluster_plot_type", label = NULL,
                     choices = c("Distribution des états" = "dplot", "Séquences individuelles" = "iplot",
                                 "Top 10 séquences" = "fplot", "Séquences représentatives" = "rplot"), selected = "dplot")
      ),
      navset_tab(
        nav_panel(
          title = "Dendrogrammes",
          layout_columns(
            col_widths = c(6, 6),
            card(full_screen = TRUE, card_header("Dendrogramme Ward "), plotOutput("dendro_simple", height = "420px")),
            card(full_screen = TRUE, card_header("Dendrogramme avec Heatmap"), plotOutput("dendro_couleur", height = "420px"))
          )
        ),
        nav_panel(
          title = "📉 Sauts d'inertie",
          layout_columns(
            col_widths = c(6, 6),
            card(full_screen = TRUE, card_header("Sauts d'inertie simples"), plotOutput("inertie_simple", height = "380px")),
            card(full_screen = TRUE, card_header("Coupures suggérées (k optimal)"), plotOutput("inertie_couleur", height = "380px"))
          )
        ),
        nav_panel(
          title = " Exploration des clusters",
          card_header(textOutput("cluster_card_title")),
          p(style = "font-size:0.85em; color:#666;", textOutput("cluster_plot_desc")),
          plotOutput("cluster_plot_out", height = "750px") 
        )
      )
    )
  ),
  
  # Onglet 3 : Analyse des Clusters
  
  nav_panel(
    title = "Exploration sémantique",
    icon  = icon("layer-group"),
    navset_card_tab(
      nav_panel(
        title = "Chaînes de coréf vs annotations du corpus",
        card_header("Détail des chaînes et enchaînements par cluster"),
        p(style = "font-size:0.85em; color:#555;",
          "Ce tableau permet de filtrer par classe pour observer la correspondance entre les chaînes de coréférences  et les annotations du corpus."),
        DTOutput("table_exploration_semantique")
      ),
      
      nav_panel(
        title = "Tableau nettoyé",
        card_header("Version nettoyée"),
        p(style = "font-size:0.85em; color:#555;",
          "Les séquences composées uniquement des 'Non annoté' ont été supprimées de ce tableau."),
        DTOutput("table_exploration_filtree")
      ),
      
      # sous onglet pour le traitement par héritage des elements Non annotés
      
      nav_panel(
        title = "Héritage des Annotations",
        card_header("Traitement par héritage "),
        p(style = "font-size:0.85em; color:#555;",
          "Dans ce tableau, les éléments 'Non annoté' ont hérité de la balise (à gauche comme à droite) la plus proche au sein de leur propre chaîne de coréférence."),
        DTOutput("table_exploration_heritage")
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
      options = list(
        pageLength = 10, 
        scrollX = TRUE,
        language = lang_fr
      ), 
      rownames = FALSE, 
      filter = "top"
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
    labels <- c(dplot = "Proportions des états", iplot = "Séquences individuelles", fplot = "Top 10 fréquences", rplot = "Médoïdes représentatifs")
    paste0(labels[input$cluster_plot_type], " | k = ", d$k, " clusters")
  })
  
  output$cluster_sizes <- renderTable({
    d <- clustering_react()
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
        Document           = doc,
        ID_chaine          = mention_id,
        Cluster            = Cluster_Affecte,
        Enchaînement_nature = sequences_SPS,
        Annotation_corpus  = sequence_XML,
        Annotation_héritée = sequence_XML_heritee, 
        Mots_contexte      = vrais_mots
      )
  })
  
  # Tableau 1 : toutes les données (Sans la colonne héritée)
  
  output$table_exploration_semantique <- renderDT({
    df_tab1 <- df_base_complet() %>% select(-Annotation_héritée)
    
    datatable(
      df_tab1,
      extensions = 'Buttons',
      options = list(
        dom = 'Bfrtip',
        buttons = list(
          list(extend = 'copy', text = 'Copier', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'csv', text = 'CSV', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'excel', text = 'Excel', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'pdf', text = 'PDF', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'print', text = 'Imprimer', exportOptions = list(modifier = list(page = "all")))
        ),
        pageLength = 10,
        scrollX = TRUE,
        searchCols = list(NULL, NULL, list(search = "Classe 1"), NULL, NULL, NULL),
        language = lang_fr
      ),
      rownames = FALSE,
      filter = "top",
      class = "stripe hover compact"
    )
  }, server = FALSE)
  
  # Tableau 2 : filtrage (Sans la colonne héritée)
  
  output$table_exploration_filtree <- renderDT({
    df_clean <- df_base_complet() %>%
      filter(!is.na(Annotation_corpus) & !grepl("^(Non annoté(\\s*->\\s*Non annoté)*)$", Annotation_corpus)) %>%
      select(-Annotation_héritée)
    
    datatable(
      df_clean,
      extensions = 'Buttons',
      options = list(
        dom = 'Bfrtip',
        buttons = list(
          list(extend = 'copy', text = 'Copier', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'csv', text = 'CSV', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'excel', text = 'Excel', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'pdf', text = 'PDF', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'print', text = 'Imprimer', exportOptions = list(modifier = list(page = "all")))
        ),
        pageLength = 10,
        scrollX = TRUE,
        searchCols = list(NULL, NULL, list(search = "Classe 1"), NULL, NULL, NULL),
        language = lang_fr
      ),
      rownames = FALSE,
      filter = "top",
      class = "stripe hover compact"
    )
  }, server = FALSE)
  
  # Tableau 3 : héritage des annotations (AVEC la colonne héritée)
  
  output$table_exploration_heritage <- renderDT({
    df_heritage <- df_base_complet() %>%
      filter(!is.na(Annotation_corpus) & !grepl("^(Non annoté(\\s*->\\s*Non annoté)*)$", Annotation_corpus))
    
    datatable(
      df_heritage,
      extensions = 'Buttons',
      options = list(
        dom = 'Bfrtip',
        buttons = list(
          list(extend = 'copy', text = 'Copier', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'csv', text = 'CSV', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'excel', text = 'Excel', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'pdf', text = 'PDF', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'print', text = 'Imprimer', exportOptions = list(modifier = list(page = "all")))
        ),
        pageLength = 10,
        scrollX = TRUE,
        searchCols = list(NULL, NULL, list(search = "Classe 1"), NULL, NULL, NULL, NULL),
        language = lang_fr
      ),
      rownames = FALSE,
      filter = "top",
      class = "stripe hover compact"
    )
  }, server = FALSE)
}

# **********************************************************************************************************************************

## Lancement de l'application

shinyApp(ui = ui, server = server)