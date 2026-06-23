# =============================================================================
# APP SHINY - Analyse de séquences de coréférence (sans singletons)
# Basée sur le script de Abdoulrazack
# =============================================================================

library(shiny)
library(bslib)
library(TraMineR)
library(TraMineRextras)
library(WeightedCluster)
library(cluster)
library(seqhandbook)
library(RColorBrewer)

# =============================================================================
# CALCULS PRÉ-SHINY (une seule fois au démarrage)
# =============================================================================

# --- 1. Chargement des données ---
# ⚠️  Mets ici le chemin vers ton fichier CSV
sequences_data <- read.csv("sequences_coreferences_sans_singleton_fr_maj.csv",
                           header       = TRUE,
                           na.strings   = '',
                           fill         = TRUE,
                           sep          = ',',
                           fileEncoding = "UTF-8")

# --- 2. Dictionnaire de couleurs ---
couleurs_dico <- c(
  "SNdef"      = "#FFFF99",
  "SNind"      = "#fb8072",
  "SNdem"      = "#80b1d3",
  "SN∅"        = "#579C91",
  "SNnum"      = "#3F84DE",
  "Poss"       = "#C45C47",
  "Pro"        = "#FDC086",
  "Np"         = "#bebada",
  "Sujet_zero" = "#96B0B7",
  "Autre"      = "#b3de69"
)

# --- 3. Détection de l'alphabet et palette ---
etats_trouves  <- seqstatl(sequences_data[, 7:24])
cpal_dynamique <- unname(couleurs_dico[etats_trouves])

# --- 4. Objet séquence ---
coref_chaines.seq <- seqdef(sequences_data[, 7:24],
                            alphabet     = etats_trouves,
                            states       = etats_trouves,
                            cpal         = cpal_dynamique,
                            with.missing = FALSE)

# --- 5. Matrice de distances OM (calcul long — fait une seule fois) ---
matrice_sub  <- seqsubm(coref_chaines.seq, method = "TRATE")
distances_om <- seqdist(coref_chaines.seq, method = "OM", indel = 1, sm = matrice_sub)

# --- 6. CAH Ward ---
arbre_ward <- agnes(as.dist(distances_om), diss = TRUE, method = "ward")

# --- 7. Ordre MDS pour tapis ---
ordre_random <- cmdscale(as.dist(distances_om), k = 1)

# --- 8. Mesures de qualité (clustrange 2–10) ---
arbre_ward.meas <- as.clustrange(arbre_ward, diss = distances_om, ncluster = 10)

# =============================================================================
# UI
# =============================================================================

ui <- page_navbar(
  title = "Analyse de séquences – Coréférence",
  theme = bs_theme(bootswatch = "flatly", base_font = font_google("Inter")),

  # ── Onglet 1 : Vue d'ensemble ─────────────────────────────────────────────
  nav_panel(
    title = "Vue d'ensemble",
    icon  = icon("chart-bar"),

    layout_sidebar(
      sidebar = sidebar(
        width = 280,
        h5("Options"),
        radioButtons("overview_plot", "Visualisation :",
                     choices = c("Trajectoires individuelles" = "iplot",
                                 "Distribution des états"     = "dplot"),
                     selected = "dplot")
      ),

      card(
        full_screen = TRUE,
        card_header("Corpus complet"),
        plotOutput("overview_plot_out", height = "520px")
      )
    )
  ),

  # ── Onglet 2 : Choix du nombre de clusters ────────────────────────────────
  nav_panel(
    title = "Choix des clusters",
    icon  = icon("sitemap"),

    layout_columns(
      col_widths = c(6, 6),

      card(
        full_screen = TRUE,
        card_header("Dendrogramme (Ward)"),
        plotOutput("dendro_plot", height = "450px")
      ),

      card(
        full_screen = TRUE,
        card_header("Sauts d'inertie"),
        plotOutput("inertie_plot", height = "200px"),
        hr(),
        card_header("Indices de qualité (ASWw, HG, PBC)"),
        plotOutput("qualite_plot", height = "220px")
      )
    )
  ),

  # ── Onglet 3 : Exploration des clusters ───────────────────────────────────
  nav_panel(
    title = "Clusters",
    icon  = icon("layer-group"),

    layout_sidebar(
      sidebar = sidebar(
        width = 300,
        h5("Paramètres"),

        sliderInput("nb_clusters", "Nombre de clusters :",
                    min = 2, max = 10, value = 4, step = 1),

        hr(),

        radioButtons("cluster_plot_type", "Visualisation :",
                     choices = c(
                       "Distribution des états (dplot)"       = "dplot",
                       "Séquences individuelles (iplot)"      = "iplot",
                       "10 séquences les + fréquentes (fplot)"= "fplot",
                       "Séquences représentatives (rplot)"    = "rplot"
                     ),
                     selected = "dplot"),

        hr(),

        h6("Taille des clusters"),
        tableOutput("cluster_sizes")
      ),

      card(
        full_screen = TRUE,
        card_header(textOutput("cluster_card_title")),
        plotOutput("cluster_plot_out", height = "550px")
      )
    )
  ),

  # ── Onglet 4 : Heatmap ────────────────────────────────────────────────────
  nav_panel(
    title = "Heatmap",
    icon  = icon("th"),

    card(
      full_screen = TRUE,
      card_header("Heatmap séquences × états (avec dendrogramme)"),
      plotOutput("heatmap_plot", height = "600px")
    )
  ),

  # ── Onglet 5 : Statistiques ───────────────────────────────────────────────
  nav_panel(
    title = "Statistiques",
    icon  = icon("table"),

    layout_columns(
      col_widths = c(6, 6),

      card(
        card_header("Distances au centre par cluster"),
        tableOutput("disscenter_table")
      ),

      card(
        card_header("Résumé des indices de qualité"),
        verbatimTextOutput("qualite_summary")
      )
    )
  )
)

# =============================================================================
# SERVER
# =============================================================================

server <- function(input, output, session) {

  # ── Clustering réactif selon nb_clusters ──────────────────────────────────
  clustering_react <- reactive({
    k   <- input$nb_clusters
    cl  <- cutree(arbre_ward, k = k)
    fac <- factor(cl, labels = paste("Classe", 1:k))
    list(cl = cl, fac = fac)
  })

  # ── Onglet 1 : Vue d'ensemble ─────────────────────────────────────────────
  output$overview_plot_out <- renderPlot({
    if (input$overview_plot == "iplot") {
      seqIplot(coref_chaines.seq,
               main        = "Trajectoires individuelles des chaînes",
               with.legend = "right")
    } else {
      seqdplot(coref_chaines.seq,
               main        = "Distribution des natures à chaque position",
               with.legend = "right")
    }
  })

  # ── Onglet 2 : Dendrogramme ───────────────────────────────────────────────
  output$dendro_plot <- renderPlot({
    plot(as.dendrogram(arbre_ward),
         main    = "Dendrogramme des chaînes de coréférence",
         leaflab = "none",
         xlab    = "Séquences",
         ylab    = "Hauteur (Inertie)")
  })

  output$inertie_plot <- renderPlot({
    plot(sort(arbre_ward$height, decreasing = TRUE)[1:15],
         type = 's',
         xlab = "Nombre de clusters",
         ylab = "Inertie",
         main = "Sauts d'inertie (Ward)",
         lwd  = 2,
         col  = "steelblue")
    abline(v = input$nb_clusters, col = "firebrick", lty = 2, lwd = 1.5)
  })

  output$qualite_plot <- renderPlot({
    plot(arbre_ward.meas, stat = c("ASWw", "HG", "PBC"), norm = "zscore")
  })

  # ── Onglet 3 : Clusters ───────────────────────────────────────────────────
  output$cluster_card_title <- renderText({
    paste("Visualisation –", input$cluster_plot_type,
          "| k =", input$nb_clusters, "clusters")
  })

  output$cluster_sizes <- renderTable({
    fac <- clustering_react()$fac
    df  <- as.data.frame(table(fac))
    colnames(df) <- c("Cluster", "n")
    df
  })

  output$cluster_plot_out <- renderPlot({
    cl_data <- clustering_react()

    if (input$cluster_plot_type == "dplot") {
      seqdplot(coref_chaines.seq,
               group  = cl_data$fac,
               border = TRUE,
               main   = paste("Distribution des états – k =", input$nb_clusters))

    } else if (input$cluster_plot_type == "iplot") {
      seqiplot(coref_chaines.seq,
               group       = cl_data$fac,
               sortv       = ordre_random,
               idxs        = 0,
               space       = 0,
               border      = NA,
               with.legend = TRUE,
               yaxis       = FALSE,
               cex.axis    = 1.2,
               cex.legend  = 0.9,
               main        = paste("Séquences individuelles – k =", input$nb_clusters))

    } else if (input$cluster_plot_type == "fplot") {
      seqfplot(coref_chaines.seq,
               group       = cl_data$fac,
               with.legend = TRUE,
               yaxis       = FALSE,
               cex.legend  = 0.9,
               main        = paste("10 séquences les + fréquentes – k =", input$nb_clusters))

    } else if (input$cluster_plot_type == "rplot") {
      seqrplot(coref_chaines.seq,
               group       = cl_data$fac,
               dist.matrix = distances_om,
               criterion   = "dist",
               cex.legend  = 0.9,
               main        = paste("Séquences représentatives – k =", input$nb_clusters))
    }
  }, height = 550)

  # ── Onglet 4 : Heatmap ────────────────────────────────────────────────────
  output$heatmap_plot <- renderPlot({
    seqhandbook::seq_heatmap(coref_chaines.seq, arbre_ward)
  })

  # ── Onglet 5 : Statistiques ───────────────────────────────────────────────
  output$disscenter_table <- renderTable({
    cl_data <- clustering_react()
    res     <- aggregate(
      disscenter(as.dist(distances_om), group = cl_data$fac),
      list(cl_data$fac),
      mean
    )
    colnames(res) <- c("Cluster", "Distance moyenne au centre")
    res
  }, digits = 4)

  output$qualite_summary <- renderPrint({
    summary(arbre_ward.meas, max.rank = 2)
  })
}

# =============================================================================
# LANCEMENT
# =============================================================================
shinyApp(ui = ui, server = server)
