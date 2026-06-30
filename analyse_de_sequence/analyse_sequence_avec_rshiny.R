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
library(dplyr) # Nécessaire pour les jointures et agrégations

# *********************************************************************************
## Chargement et Préparation des Données

# Chargement des données séquences 

sequences_data <- read.csv(
  "sequences_coreferences_francais.csv",
  header       = TRUE,
  na.strings   = '',
  fill         = TRUE,
  sep          = ',',
  fileEncoding = "UTF-8"
)

# Chargement des données de croisement (temporalité + coref)

comparaison_data <- read.csv(
  "comparaison_coref_temp.csv",
  header       = TRUE,
  sep          = ',',
  fileEncoding = "UTF-8"
)

# Reconstruction maillon par maillon

df_valid <- comparaison_data %>% filter(mention_id != "Non applicable" & !is.na(mention_id))
chaines_uniques <- df_valid %>% select(doc, mention_id, chaine_complete) %>% distinct()

xml_reconstruit_list <- lapply(1:nrow(chaines_uniques), function(i) {
  current_doc   <- chaines_uniques$doc[i]
  current_mid   <- chaines_uniques$mention_id[i]
  current_chaine <- chaines_uniques$chaine_complete[i]
  
  # On sépare les têtes lexicales dans leur ordre d'apparition 
  
  heads <- unlist(strsplit(as.character(current_chaine), ",\\s*"))
  
  # On récupère les annotations disponibles pour le cluster
  
  df_sub <- df_valid %>% filter(doc == current_doc, mention_id == current_mid)
  ent_list_low <- tolower(trimws(as.character(df_sub$entité)))
  
  # Fonction pour trouver le meilleur index de correspondance
  
  trouver_index <- function(h) {
    h_low <- tolower(trimws(h))
    
    # Match simple
    
    exact_idx <- which(ent_list_low == h_low)
    if (length(exact_idx) > 0) return(exact_idx[1])
    
    # Match par mot entier 
    # Échappement des caractères spéciaux au cas où
    
    h_escaped <- gsub("([.|()\\^{}+$*?]|\\[|\\])", "\\\\\\1", h_low)
    pattern <- paste0("\\b", h_escaped, "\\b")
    
    match_idx <- which(sapply(ent_list_low, function(ent_low) {
      ent_escaped <- gsub("([.|()\\^{}+$*?]|\\[|\\])", "\\\\\\1", ent_low)
      pattern_ent <- paste0("\\b", ent_escaped, "\\b")
      # Match en mot entier dans un sens ou dans l'autre
      grepl(pattern, ent_low, perl=TRUE) || grepl(pattern_ent, h_low, perl=TRUE)
    }))
    
    if (length(match_idx) > 0) return(match_idx[1])
    
    # Match simple 
    fallback_idx <- which(sapply(ent_list_low, function(ent_low) {
      grepl(h_low, ent_low, fixed = TRUE) || grepl(ent_low, h_low, fixed = TRUE)
    }))
    
    if (length(fallback_idx) > 0) return(fallback_idx[1])
    
    return(NA) # Aucun match trouvé
  }
  
  # Application de l'algorithme à toutes les têtes
  
  indices <- sapply(heads, trouver_index)
  
  # Reconstruction des séquences alignées
  
  xml_types <- sapply(1:length(heads), function(idx) {
    if (!is.na(indices[idx])) as.character(df_sub$type_temporalite[indices[idx]]) else "Non annoté"
  })
  
  mots_classes <- sapply(1:length(heads), function(idx) {
    if (!is.na(indices[idx])) as.character(df_sub$entité[indices[idx]]) else heads[idx]
  })
  
  # Retourne une structurepar chaîne
  
  data.frame(
    doc = current_doc,
    mention_id = current_mid,
    sequence_XML = paste(xml_types, collapse = " -> "),
    vrais_mots = paste(mots_classes, collapse = ", "),
    stringsAsFactors = FALSE
  )
})

# Fusion du dictionnaire réaligné

xml_reconstruit <- do.call(rbind, xml_reconstruit_list)


# Dictionnaire de couleurs pour TraMineR

couleurs_dico <- c(
  "SNdef"      = "#FFFF99",
  "SNind"      = "#fb8072",
  "SNdem"      = "#80b1d3",
  "SN\u2205"   = "#579C91",
  "SNnum"      = "#3F84DE",
  "Poss"       = "#C45C47",
  "Pro"        = "#7B1FA2",                
  "Np"         = "#FDC086",
  "Sujet_zero" = "#96B0B7",
  "SNposs"     = "#FF0000",
  "Autre"      = "#b3de69"
)

# Alphabet et palette dynamique

etats_trouves  <- seqstatl(sequences_data[, 7:24])
cpal_dynamique <- unname(couleurs_dico[etats_trouves])

# Objet séquence TraMineR 

coref_chaines.seq <- seqdef(
  sequences_data[, 7:24],
  alphabet     = etats_trouves,
  states       = etats_trouves,
  cpal         = cpal_dynamique,
  with.missing = FALSE
)

# Format compressé SPS pour affichage

sequences_SPS <- seqformat(
  sequences_data, 7:24,
  from = "STS", to = "SPS",
  compress = TRUE, with.missing = FALSE
)
sequences_data$sequences_SPS <- sequences_SPS

# Matrice de distances OM

matrice_sub  <- seqsubm(coref_chaines.seq, method = "TRATE")
distances_om <- seqdist(coref_chaines.seq, method = "OM", indel = 1, sm = matrice_sub)

# CAH méthode Ward 

arbre_ward   <- agnes(as.dist(distances_om), diss = TRUE, method = "ward")
ordre_random <- cmdscale(as.dist(distances_om), k = 1)

# Calcul des sauts d'inertie

hauteurs         <- sort(arbre_ward$height, decreasing = TRUE)[1:15]
sauts            <- diff(hauteurs)
grands_sauts_idx <- order(abs(sauts), decreasing = TRUE)[1:4]
couleurs_sauts   <- c("#E74C3C", "#FFFF00", "#8E44AD", "#27AE60")

# Fonction Heatmap 

seq_heatmap_custom <- function(seq, tree, with.missing = FALSE, ...) {
  if (!inherits(tree, "dendrogram")) tree <- as.dendrogram(tree)
  mat <- seq
  for (i in seq_len(length(seq))) {
    mat[mat[, i] == "%", i] <- NA
    mat[, i] <- as.numeric(mat[, i])
  }
  mat <- as.matrix(mat)
  col <- attr(seq, "cpal")
  if (with.missing) col <- c(col, attr(seq, "missing.color"))
  heatmap(mat, tree, NA, na.rm = FALSE, col = col, scale = "none", labRow = NA, ...)
}

# *********************************************************************************************
## Interface Utilisateur (UI)

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
    title = "Choix du cluster",
    icon  = icon("sitemap"),
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
      )
    )
  ),
  
  # Onglet 3 : Analyse des Clusters
  nav_panel(
    title = "Analyse des Clusters",
    icon  = icon("layer-group"),
    layout_sidebar(
      sidebar = sidebar(
        width = 300,
        h5("Configuration"),
        sliderInput("nb_clusters", label = "Nombre de classes (k) :", min = 2, max = 10, value = 4, step = 1),
        hr(),
        h6("Tailles"),
        tableOutput("cluster_sizes"),
        hr(),
        h6("Type de Graphique"),
        radioButtons("cluster_plot_type", label = NULL,
                     choices = c("Distribution des états" = "dplot", "Séquences individuelles" = "iplot",
                                 "Top 10 séquences" = "fplot", "Séquences représentatives" = "rplot"), selected = "dplot")
      ),
      navset_card_tab(
        nav_panel(
          title = " Graphiques TraMineR",
          card_header(textOutput("cluster_card_title")),
          p(style = "font-size:0.85em; color:#666;", textOutput("cluster_plot_desc")),
          plotOutput("cluster_plot_out", height = "750px") 
        ),
        
        nav_panel(
          title = "Exploration Sémantique (temporalité vs coref)",
          card_header("Détail des chaînes et enchaînements par cluster"),
          p(style = "font-size:0.85em; color:#555;",
            "Ce tableau permet de filtrer par classe pour observer la correspondance. Il peut être téléchargeable via les boutons ci-dessous."),
          DTOutput("table_exploration_semantique")
        )
      )
    )
  )
)

# ************************************************************************************************************************
## Serveur 

server <- function(input, output, session) {
  
  # Objet réactif pour le découpage des clusters
  clustering_react <- reactive({
    k   <- input$nb_clusters
    cl  <- cutree(arbre_ward, k = k)
    fac <- factor(cl, labels = paste("Classe", 1:k))
    list(cl = cl, fac = fac, k = k)
  })
  
  # Onglet 1 : Vue d'ensemble 
  
  output$nb_sequences <- renderText({ nrow(sequences_data) })
  output$nb_colonnes  <- renderText({ ncol(sequences_data) })
  output$nb_etats     <- renderText({ length(etats_trouves) })
  
  output$table_sequences_data <- renderDT({
    datatable(
      sequences_data, 
      options = list(
        pageLength = 10, 
        scrollX = TRUE,
        language = list(url = "//cdn.datatables.net/plug-ins/1.13.6/i18n/fr-FR.json")
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
  
  # Onglet 2 : Dendrogrammes & Sauts 
  
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
  
  # Onglet 3 : Analyse des Clusters 
  
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
  
  # Couplage dynamique (coref vs temporalité) avec fonctionnalité d'export
  output$table_exploration_semantique <- renderDT({
    d <- clustering_react()
    
    # Copie du dataframe de base et injection du cluster courant
    df_analyse <- sequences_data
    df_analyse$Cluster_Affecte <- d$fac
    
    # Jointure SQL réactive avec les enchaînements réalignés
    df_complet <- df_analyse %>%
      left_join(xml_reconstruit, by = c("doc", "mention_id")) %>%
      select(
        Document           = doc,
        ID_chaine          = mention_id,
        Cluster            = Cluster_Affecte,
        Enchaînement_nature = sequences_SPS,
        Annotation_corpus  = sequence_XML,
        Mots_contexte      = vrais_mots
      )
    
    # Rendu du tableau DataTables avec l'extension "Buttons
    
    datatable(
      df_complet,
      extensions = 'Buttons',
      options = list(
        dom = 'Bfrtip',
        # Ajoute du paramètre "page = 'all'" pour s'assurer que l'export télécharge la totalité des lignes 
        buttons = list(
          list(extend = 'copy', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'csv', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'excel', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'pdf', exportOptions = list(modifier = list(page = "all"))),
          list(extend = 'print', exportOptions = list(modifier = list(page = "all")))
        ),
        pageLength = 10,
        scrollX = TRUE,
        searchCols = list(NULL, NULL, list(search = "Classe 1"), NULL, NULL, NULL),
        language = list(url = "//cdn.datatables.net/plug-ins/1.13.6/i18n/fr-FR.json")
      ),
      rownames = FALSE,
      filter = "top",
      class = "stripe hover compact"
    )
  }, server = FALSE) #   permet l'export complet 
}

# **********************************************************************************************************************************

## Lancement de l'application

shinyApp(ui = ui, server = server)