import java.awt.Color;
import java.awt.Font;
import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import org.gephi.appearance.api.AppearanceController;
import org.gephi.appearance.api.AppearanceModel;
import org.gephi.appearance.api.Function;
import org.gephi.appearance.api.Partition;
import org.gephi.appearance.api.PartitionFunction;
import org.gephi.appearance.plugin.PartitionElementColorTransformer;
import org.gephi.appearance.plugin.RankingNodeSizeTransformer;
import org.gephi.graph.api.Column;
import org.gephi.graph.api.Edge;
import org.gephi.graph.api.Graph;
import org.gephi.graph.api.GraphController;
import org.gephi.graph.api.GraphModel;
import org.gephi.graph.api.Node;
import org.gephi.graph.api.Table;
import org.gephi.io.exporter.api.ExportController;
import org.gephi.io.importer.api.Container;
import org.gephi.io.importer.api.EdgeDirectionDefault;
import org.gephi.io.importer.api.ImportController;
import org.gephi.io.processor.plugin.DefaultProcessor;
import org.gephi.preview.api.PreviewController;
import org.gephi.preview.api.PreviewModel;
import org.gephi.preview.api.PreviewProperty;
import org.gephi.project.api.ProjectController;
import org.gephi.project.api.Workspace;
import org.gephi.statistics.plugin.GraphDistance;
import org.gephi.statistics.plugin.PageRank;
import org.openide.util.Lookup;

/** Betweenness centrality + PageRank on the Tamaulipas Municipio<->Sustancia
 * bipartite graph, computed by Gephi's own Statistics engine (not
 * reimplemented in Python). Node size = betweenness (reveals bridge nodes);
 * PageRank is kept as a node attribute for the HTML hover / GEXF. Two-column
 * layout again - this is the same dense bipartite graph that collapses
 * under any force-directed layout. */
/** args: input.gexf outDir [fa2]   (fa2 = ForceAtlas2 layout instead of two columns; outputs get the suffix _fa2) */
public class GephiCentralidad {

    private static Column findColumnByTitleContains(Table table, String needle) {
        for (Column c : table) {
            if (c.getTitle().toLowerCase().contains(needle.toLowerCase())) {
                return c;
            }
        }
        throw new IllegalStateException("No column with title containing '" + needle + "' found");
    }

    public static void main(String[] args) throws Exception {
        String inputGexf = args.length > 0 ? args[0] : "tamaulipas.gexf";
        String outDir = args.length > 1 ? args[1] : ".";

        ProjectController pc = Lookup.getDefault().lookup(ProjectController.class);
        pc.newProject();
        Workspace workspace = pc.getCurrentWorkspace();

        ImportController importController = Lookup.getDefault().lookup(ImportController.class);
        Container container = importController.importFile(new File(inputGexf));
        container.getLoader().setEdgeDefault(EdgeDirectionDefault.UNDIRECTED);
        container.getLoader().setAllowAutoNode(false);
        importController.process(container, new DefaultProcessor(), workspace);

        GraphModel graphModel = Lookup.getDefault().lookup(GraphController.class).getGraphModel(workspace);
        Graph graph = graphModel.getUndirectedGraph();
        System.out.println("Imported nodes=" + graph.getNodeCount() + " edges=" + graph.getEdgeCount());

        // Gephi's own Statistics engine - real betweenness centrality + PageRank
        GraphDistance distance = new GraphDistance();
        distance.setDirected(false);
        distance.execute(graphModel);

        PageRank pageRank = new PageRank();
        pageRank.setDirected(false);
        pageRank.execute(graphModel);

        Table nodeTable = graphModel.getNodeTable();
        System.out.println("Node table columns after statistics:");
        for (Column c : nodeTable) {
            System.out.println("  id=" + c.getId() + " title=" + c.getTitle());
        }

        Column typeColumn = findColumnByTitleContains(nodeTable, "type");
        Column totalKgColumn = findColumnByTitleContains(nodeTable, "total_kg");
        Column betweennessColumn = findColumnByTitleContains(nodeTable, "betweenness");
        Column pageRankColumn = findColumnByTitleContains(nodeTable, "pagerank");

        // Two-column bipartite layout (proven pattern for this dense graph),
        // this time ranked by BETWEENNESS rather than total_kg - the point of
        // this view is to surface bridge nodes, not just big emitters.
        List<Node> locNodes = new ArrayList<>();
        List<Node> subNodes = new ArrayList<>();
        for (Node n : graph.getNodes()) {
            String kind = String.valueOf(n.getAttribute(typeColumn));
            (kind.equals("location") ? locNodes : subNodes).add(n);
        }
        Comparator<Node> byBetweennessDesc = Comparator.comparingDouble(
                (Node n) -> ((Number) n.getAttribute(betweennessColumn)).doubleValue()).reversed();
        locNodes.sort(byBetweennessDesc);
        subNodes.sort(byBetweennessDesc);

        boolean useFa2 = args.length > 2 && args[2].equals("fa2");
        String suffix = useFa2 ? "_fa2" : "";

        if (useFa2) {
            // ForceAtlas2 with edge weights IGNORED: extreme weight skew
            // (Altamira / Bioxido de carbono ~1000x the rest) is what collapsed it before.
            org.gephi.layout.plugin.forceAtlas2.ForceAtlas2 layout =
                    new org.gephi.layout.plugin.forceAtlas2.ForceAtlas2Builder().buildLayout();
            layout.setGraphModel(graphModel);
            layout.resetPropertiesValues();
            layout.setEdgeWeightInfluence(0.0);
            layout.setScalingRatio(150.0);
            layout.setGravity(1.0);
            layout.setOutboundAttractionDistribution(true);
            layout.setAdjustSizes(true);
            layout.setJitterTolerance(1.0);
            layout.initAlgo();
            int steps = 0;
            while (layout.canAlgo() && steps < 3000) {
                layout.goAlgo();
                steps++;
            }
            layout.endAlgo();
            System.out.println("FA2 ran " + steps + " steps");
        } else {
            float totalHeight = 6000f;
            float colX = 900f;
            for (int i = 0; i < locNodes.size(); i++) {
                float t = locNodes.size() > 1 ? (float) i / (locNodes.size() - 1) : 0f;
                locNodes.get(i).setX(-colX);
                locNodes.get(i).setY(t * totalHeight);
            }
            for (int i = 0; i < subNodes.size(); i++) {
                float t = subNodes.size() > 1 ? (float) i / (subNodes.size() - 1) : 0f;
                subNodes.get(i).setX(colX);
                subNodes.get(i).setY(t * totalHeight);
            }
        }

        AppearanceController appearanceController = Lookup.getDefault().lookup(AppearanceController.class);
        AppearanceModel appearanceModel = appearanceController.getModel(workspace);

        Function partitionFunction = appearanceModel.getNodeFunction(typeColumn, PartitionElementColorTransformer.class);
        Partition partition = ((PartitionFunction) partitionFunction).getPartition();
        for (Object value : partition.getValues(graph)) {
            String v = String.valueOf(value);
            Color color = v.equals("location") ? new Color(0x2a, 0x78, 0xd6) : new Color(0xeb, 0x68, 0x34);
            partition.setColor(value, color);
        }
        appearanceController.transform(partitionFunction);

        Function sizeFunction = appearanceModel.getNodeFunction(betweennessColumn, RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer sizeTransformer = (RankingNodeSizeTransformer) sizeFunction.getTransformer();
        sizeTransformer.setMinSize(6);
        sizeTransformer.setMaxSize(55);
        appearanceController.transform(sizeFunction);

        for (Edge e : graph.getEdges()) {
            e.setColor(new Color(0x89, 0x87, 0x81, 90));
        }

        // Print top-10 bridge nodes for the record
        List<Node> byBetweenness = new ArrayList<>();
        for (Node n : graph.getNodes()) byBetweenness.add(n);
        byBetweenness.sort(byBetweennessDesc);
        System.out.println("Top 10 by betweenness centrality:");
        for (int i = 0; i < Math.min(10, byBetweenness.size()); i++) {
            Node n = byBetweenness.get(i);
            System.out.println("  " + n.getAttribute(betweennessColumn) + "  " + n.getLabel()
                    + "  (pagerank=" + n.getAttribute(pageRankColumn) + ")");
        }

        PreviewController previewController = Lookup.getDefault().lookup(PreviewController.class);
        PreviewModel previewModel = previewController.getModel(workspace);
        previewModel.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_FONT, new Font("Arial", Font.PLAIN, 10));
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_SHOW_BOX, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_OPACITY, 90f);
        previewModel.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.6f);
        previewModel.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, new Color(0xfc, 0xfc, 0xfb));
        previewModel.getProperties().putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 55f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, 1.2f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);

        File gexfOut = new File(outDir, "centralidad_toolkit" + suffix + ".gexf");
        exportController.exportFile(gexfOut);
        System.out.println("Written " + gexfOut.getAbsolutePath());

        File pdfOut = new File(outDir, "centralidad_toolkit" + suffix + ".pdf");
        exportController.exportFile(pdfOut);
        System.out.println("Written " + pdfOut.getAbsolutePath());

        try {
            File pngOut = new File(outDir, "centralidad_toolkit" + suffix + ".png");
            org.gephi.io.exporter.preview.PNGExporter pngExporter =
                    (org.gephi.io.exporter.preview.PNGExporter) exportController.getExporter("png");
            pngExporter.setWorkspace(workspace);
            pngExporter.setWidth(useFa2 ? 1800 : 1400);
            pngExporter.setHeight(useFa2 ? 1600 : 2600);
            pngExporter.setTransparentBackground(false);
            exportController.exportFile(pngOut, pngExporter);
            System.out.println("Written " + pngOut.getAbsolutePath());
        } catch (Exception ex) {
            System.out.println("PNG export failed:");
            ex.printStackTrace(System.out);
        }

        System.out.println("DONE");
    }
}
