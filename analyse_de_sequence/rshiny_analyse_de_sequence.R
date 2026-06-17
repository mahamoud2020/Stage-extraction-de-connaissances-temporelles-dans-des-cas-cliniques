# Packages nécessaires 

library(shiny)
library(bslib)
library(TraMineR)
library(TraMineRextras)
library(WeightedCluster)
library(cluster)
library(seqhandbook)
library(dendextend)
library(RColorBrewer)
library(DT)           # pour afficher le dataframe interactif



# Chargement des données 

sequences_data <- read.csv(
  "sequences_coreferences_francais.csv",
  header       = TRUE,
  na.strings   = '',
  fill         = TRUE,
  sep          = ',',
  fileEncoding = "UTF-8"
)

# Dictionnaire de couleurs

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

# Format SPS 


sequences_SPS <- seqformat(sequences_data, 7:24,
                                          from = "STS", to = "SPS",
                                          compress = TRUE, with.missing = FALSE)

sequences_data$sequences_SPS <- sequences_SPS



# Matrice de distances OM (calcul long, fait une seule fois)

matrice_sub  <- seqsubm(coref_chaines.seq, method = "TRATE")

distances_om <- seqdist(coref_chaines.seq, method = "OM", indel = 1, sm = matrice_sub)

# CAH Ward 

arbre_ward <- agnes(as.dist(distances_om), diss = TRUE, method = "ward")

# 
ordre_random <- cmdscale(as.dist(distances_om), k = 1)

# Clustr

arbre_ward.meas <- as.clustrange(arbre_ward, diss = distances_om, ncluster = 10)

# Fonction seq_heatmap 

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
  heatmap(mat, tree, NA, na.rm = FALSE, col = col,
          scale = "none", labRow = NA, ...)
}

# Sauts d'inertie 

hauteurs         <- sort(arbre_ward$height, decreasing = TRUE)[1:15]
sauts            <- diff(hauteurs)
grands_sauts_idx <- order(abs(sauts), decreasing = TRUE)[1:4]
couleurs_sauts   <- c("#E74C3C", "#FFFF00", "#8E44AD", "#27AE60")



# UI


ui <- page_navbar(
  title = "Analyse de séquences appliquée aux chaînes de Coréférences",
  theme = bs_theme(bootswatch = "flatly", base_font = font_google("Inter")),

  
  # Onglet 1 : Vue d'ensemble 
  
  nav_panel(
    title = "Vue d'ensemble",
    icon  = icon("table"),

    navset_tab(

      # Sous-onglet A : Présentation du jeu de données 
      nav_panel(
        title = "📋 Présentation des données",

        card(
          card_header("Jeu de données : sequences_coreferences_francais.csv"),
          p(style = "color:#555; font-size:0.9em;",
            "Aperçu général du jeu de données utilisé :\n 
             Chaque ligne correspond à une chaîne de coréférence.\n",
            " Les colonnes 7 à 24 contiennent les états de la séquence (nature)."),
            
          hr(),
          layout_columns(
            col_widths = c(4, 4, 4),
            value_box(title = "Nombre de chaînes",
                      value = textOutput("nb_sequences"),
                      showcase = icon("list"),
                      theme  = "primary"),
            value_box(title = "Colonnes",
                      value = textOutput("nb_colonnes"),
                      showcase = icon("columns"),
                      theme  = "success"),
            value_box(title = "États distincts",
                      value = textOutput("nb_etats"),
                      showcase = icon("palette"),
                      theme  = "info")
          ),
          hr(),
          DTOutput("table_sequences_data")
        )
      ),

      # ── Sous-onglet B : Visualisation ───────────────────────────────────────
      nav_panel(
        title = "📊 Visualisation",

        layout_sidebar(
          sidebar = sidebar(
            width = 260,
            h5("Options"),
            p(style = "font-size:0.85em; color:#666;",
              "Sélectionnez le type de graphique à afficher sur le corpus."),
            radioButtons(
              "vue_plot_type",
              label = "Graphique :",
              choices = c(
                "Trajectoires individuelles" = "iplot",
                "Distribution des états"     = "dplot"
              ),
              selected = "dplot"
            ),
            hr(),
            p(style = "font-size:0.8em; color:#999;",
              strong("Trajectoires individuelles (iplot) : "),
              "une ligne par séquence, les couleurs indiquent la nature à chaque position."),
            p(style = "font-size:0.8em; color:#999;",
              strong("Distribution des états (dplot) : "),
              "proportion de chaque nature référentielle à chaque position de la chaîne.")
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

      # ── Sous-onglet A : Dendrogrammes ───────────────────────────────────────
      nav_panel(
        title = "🌳 Dendrogrammes",

        p(style = "font-size:0.88em; color:#555; padding:8px 4px 0 4px;",
          "La Classification Ascendante Hiérarchique (CAH) est réalisée avec la méthode de Ward.",
          " Le dendrogramme aide à repérer visuellement les grandes familles de séquences."),
          

        layout_columns(
          col_widths = c(6, 6),

          card(
            full_screen = TRUE,
            card_header("Dendrogramme simple"),
            p(style = "font-size:0.82em; color:#777; padding:4px 8px 0 8px;",
              "Version classique : hauteurs de fusion en ordonnée, séquences en abscisse.",
              " Chaque bifurcation représente un regroupement. Plus la hauteur est grande,",
              " plus les groupes fusionnés sont dissimilaires."),
            plotOutput("dendro_simple", height = "420px")
          ),

          card(
            full_screen = TRUE,
            card_header("Dendrogramme avec heatmap"),
            p(style = "font-size:0.82em; color:#777; padding:4px 8px 0 8px;",
              "Version enrichie : la heatmap associe à chaque séquence (ligne) la nature référentielle",
              " à chaque position (colonne). Les séquences sont réordonnées selon l'arbre Ward,",
              " faisant apparaître les groupes homogènes."),
            plotOutput("dendro_couleur", height = "420px")
          )
        )
      ),

      # Sous-onglet B : Sauts d'inertie ─────────────────────────────────────
      nav_panel(
        title = "📉 Sauts d'inertie",

        p(style = "font-size:0.88em; color:#555; padding:8px 4px 0 4px;",
          "Les sauts d'inertie permettent de choisir le nombre optimal de clusters.",
          " On cherche le ", strong("grand saut"), " sur la courbe : il correspond au moment où",
          " fusionner deux groupes coûte beaucoup en termes d'homogénéité interne."),
          

        layout_columns(
          col_widths = c(6, 6),

          card(
            full_screen = TRUE,
            card_header("Sauts d'inertie  simple "),
            p(style = "font-size:0.82em; color:#777; padding:4px 8px 0 8px;",
              "Courbe en escalier des 15 premières hauteurs de fusion, triées par ordre décroissant.",
              " L'axe X représente le nombre de clusters, l'axe Y la hauteur de fusion (inertie)."),
            plotOutput("inertie_simple", height = "380px")
          ),

          card(
            full_screen = TRUE,
            card_header("Sauts d'inertie avec couleurs"),
            p(style = "font-size:0.82em; color:#777; padding:4px 8px 0 8px;",
              "Version améliorée : les 4 plus grands sauts sont mis en évidence par des points colorés",
              " et des lignes verticales pointillées. Les étiquettes ", code("k = x"),
              " indiquent les coupures candidates."),
            plotOutput("inertie_couleur", height = "380px")
          )
        )
      )
    )
  ),

  
  # Onglet 3  : Clusters 
  
  nav_panel(
    title = "Clusters",
    icon  = icon("layer-group"),

    layout_sidebar(
      sidebar = sidebar(
        width = 290,

        h5("Paramètres"),

        p(style = "font-size:0.85em; color:#666;",
          "Choisissez le nombre de clusters en déplaçant le curseur.",
          " L'arbre Ward est recoupé dynamiquement avec ", code("cutree()"),
          " et toutes les visualisations se mettent à jour automatiquement."),

        sliderInput(
          "nb_clusters",
          label   = "Nombre de clusters :",
          min     = 2,
          max     = 10,
          value   = 4,
          step    = 1,
          animate = FALSE
        ),

        hr(),

        h6("Taille des clusters"),
        p(style = "font-size:0.8em; color:#999;",
          "Répartition des séquences dans les classes après découpage de l'arbre."),
        tableOutput("cluster_sizes"),

        hr(),

        h6("Visualisation"),
        p(style = "font-size:0.85em; color:#666;",
          "Sélectionnez le type de graphique à afficher pour les clusters."),
        radioButtons(
          "cluster_plot_type",
          label   = NULL,
          choices = c(
            "Distribution des états"            = "dplot",
            "Séquences individuelles"           = "iplot",
            "10 séquences les + fréquentes"     = "fplot",
            "Séquences représentatives"         = "rplot"
          ),
          selected = "dplot"
        )
      ),

      card(
        full_screen = TRUE,
        card_header(textOutput("cluster_card_title")),
        p(style = "font-size:0.85em; color:#666; padding: 0 4px;",
          textOutput("cluster_plot_desc")),
        plotOutput("cluster_plot_out", height = "580px")
      )
    )
  )
)



# Server 


server <- function(input, output, session) {

  # ── Clustering réactif ───────────────────────────────────────────────────────
  clustering_react <- reactive({
    k   <- input$nb_clusters
    cl  <- cutree(arbre_ward, k = k)
    fac <- factor(cl, labels = paste("classe", 1:k))
    list(cl = cl, fac = fac, k = k)
  })


  
  # Onglet 1A — Présentation des données
  

  output$nb_sequences <- renderText({ nrow(sequences_data) })
  output$nb_colonnes  <- renderText({ ncol(sequences_data) })
  output$nb_etats     <- renderText({ length(etats_trouves) })

  output$table_sequences_data <- renderDT({
    datatable(
      sequences_data,
      options = list(
        pageLength  = 15,
        scrollX     = TRUE,
        lengthMenu  = list(c(10, 15, 25, 50, -1), c("10","15","25","50","Tout")),
        language    = list(
          url = "//cdn.datatables.net/plug-ins/1.13.6/i18n/fr-FR.json"
        )
      ),
      rownames = FALSE,
      filter   = "top",
      class    = "stripe hover compact"
    )
  })


  
  # Onglet 1B — Visualisation (vue d'ensemble)
  

  output$vue_plot_title <- renderText({
    if (input$vue_plot_type == "iplot")
      "Trajectoires individuelles"
    else
      "Distribution des différents natures constituant les séquences"
  })

  output$vue_plot_out <- renderPlot({
    if (input$vue_plot_type == "iplot") {
      seqIplot(coref_chaines.seq,
               main        = "Trajectoires individuelles",
               with.legend = "right")
    } else {
      seqdplot(coref_chaines.seq,
               main        = "Distribution des natures",
               with.legend = "right")
    }
  }, res = 100)


  
  # Onglet 2A — Dendrogrammes
  

  # Dendrogramme simple (sans couleur)
  output$dendro_simple <- renderPlot({
    plot(
      as.dendrogram(arbre_ward),
      main    = "Dendrogramme des chaînes de coréférence",
      leaflab = "none",
      xlab    = "Séquences",
      ylab    = "Hauteur (Inertie)"
    )
  }, res = 100)

  # Dendrogramme coloré (heatmap)
  output$dendro_couleur <- renderPlot({
    seq_heatmap_custom(coref_chaines.seq, arbre_ward)
  }, res = 100)


  
  # Onglet 2B — Sauts d'inertie
  

  # Version simple
  output$inertie_simple <- renderPlot({
    plot(
      sort(arbre_ward$height, decreasing = TRUE)[1:15],
      type = 's',
      xlab = "Nombre de clusters",
      ylab = "Inertie",
      main = "Sauts d'inertie (Critère de Ward)",
      lwd  = 2,
      col  = "blue"
    )
  }, res = 100)

  # Version annotée et colorée
  output$inertie_couleur <- renderPlot({
    plot(hauteurs,
         type     = 's',
         xlab     = "Nombre de clusters",
         ylab     = "Hauteur de fusion (inertie)",
         main     = "Sauts d'inertie — Critère de Ward",
         lwd      = 2.5,
         col      = "steelblue",
         bty      = "l",
         las      = 1,
         cex.axis = 0.9,
         cex.lab  = 1.05,
         cex.main = 1.15)

    abline(v   = grands_sauts_idx,
           lty = 2,
           col = adjustcolor(couleurs_sauts, alpha.f = 0.4),
           lwd = 1.5)

    points(grands_sauts_idx,
           hauteurs[grands_sauts_idx],
           pch = 21,
           cex = 2.5,
           bg  = couleurs_sauts,
           col = "white",
           lwd = 1.5)

    text(grands_sauts_idx,
         hauteurs[grands_sauts_idx],
         labels = paste0("k = ", grands_sauts_idx),
         pos    = 1,
         offset = 0.8,
         col    = couleurs_sauts,
         cex    = 0.95,
         font   = 2)

    legend("topright",
           legend   = paste0("k = ", sort(grands_sauts_idx)),
           pch      = 21,
           pt.bg    = couleurs_sauts[order(grands_sauts_idx)],
           col      = "gray40",
           pt.cex   = 1.8,
           cex      = 0.85,
           bty      = "n",
           title    = "Coupures possibles",
           title.col = "gray30")
  }, res = 100)


  
  # Onglet 3 — Clusters
  

  # Titre 
  output$cluster_card_title <- renderText({
    d <- clustering_react()
    labels <- c(
      dplot = "Distribution des états dans les clusters",
      iplot = "Séquences individuelles par cluster",
      fplot = "10 séquences les plus fréquentes par classe",
      rplot = "Séquences représentatives de chaque classe"
    )
    paste0(labels[input$cluster_plot_type], "  |  k = ", d$k, " clusters")
  })

  # Description du graphique
  output$cluster_plot_desc <- renderText({
    switch(input$cluster_plot_type,
      dplot = paste0("Proportion de chaque nature référentielle à chaque position,",
                     " séparée par cluster. Permet d'identifier le profil dominant de chaque classe."),
      iplot = paste0("Tapis de séquences individuelles, triées par ordre MDS au sein de chaque cluster.",
                     " Chaque ligne est une chaîne, chaque couleur une nature référentielle."),
      fplot = paste0("Les 10 séquences les plus fréquentes dans chaque classe.",
                     " Donne un aperçu des trajectoires typiques."),
      rplot = paste0("Séquences représentatives (médoïdes) de chaque classe,",
                     " sélectionnées par distance minimale au centre du cluster.")
    )
  })

  # Taille des clusters
  output$cluster_sizes <- renderTable({
    d  <- clustering_react()
    df <- as.data.frame(table(d$fac))
    colnames(df) <- c("Cluster", "n")
    df
  }, striped = TRUE, hover = TRUE, bordered = FALSE, spacing = "xs")

  # Graphique des clusters
  output$cluster_plot_out <- renderPlot({
    d <- clustering_react()

    if (input$cluster_plot_type == "dplot") {
      seqdplot(coref_chaines.seq,
               group  = d$fac,
               border = TRUE,
               main   = paste("Profil des", d$k, "classes de coréférence"))

    } else if (input$cluster_plot_type == "iplot") {
      seqiplot(coref_chaines.seq,
               group       = d$fac,
               sortv       = ordre_random,
               idxs        = 0,
               space       = 0,
               border      = NA,
               with.legend = TRUE,
               yaxis       = FALSE,
               cex.axis    = 1.5,
               cex.legend  = 1)

    } else if (input$cluster_plot_type == "fplot") {
      seqfplot(coref_chaines.seq,
               group       = d$fac,
               with.legend = TRUE,
               yaxis       = FALSE,
               cex.legend  = 1)

    } else if (input$cluster_plot_type == "rplot") {
      seqrplot(coref_chaines.seq,
               group       = d$fac,
               dist.matrix = distances_om,
               criterion   = "dist",
               cex.legend  = 1)
    }
  }, height = 580, res = 100)

}


# Lancement

shinyApp(ui = ui, server = server)
