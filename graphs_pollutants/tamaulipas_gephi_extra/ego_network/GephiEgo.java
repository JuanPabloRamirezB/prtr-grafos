import java.awt.Color;
import java.awt.Font;
import java.io.File;

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
import org.openide.util.Lookup;

/** Ego network of Altamira: small enough (24 nodes, 81 edges) that real
 * ForceAtlas2 actually works here, unlike the full dense bipartite graph. */
/** args: input.gexf outDir [fa2]   (fa2 = ForceAtlas2 with edge-weight influence 0 instead of the concentric layout) */
public class GephiEgo {

    private static Column findColumnByTitle(Table table, String title) {
        for (Column c : table) {
            if (c.getTitle().equalsIgnoreCase(title)) {
                return c;
            }
        }
        throw new IllegalStateException("No column titled '" + title + "' found");
    }

    public static void main(String[] args) throws Exception {
        String inputGexf = args.length > 0 ? args[0] : "ego_altamira.gexf";
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

        Table nodeTable = graphModel.getNodeTable();
        Column roleColumn = findColumnByTitle(nodeTable, "role");
        Column totalKgColumn = findColumnByTitle(nodeTable, "total_kg");

        // Layout - ForceAtlas2 collapses this too: Bioxido de carbono and Altamira
        // carry such extreme edge weights (Altamira alone is ~1000x the next
        // municipio) that they dominate the physics and pull everything into one
        // pile, same failure mode as the full bipartite graph. A classic
        // concentric ego-network layout - focal at the center, hop-1 substances on
        // an inner ring, hop-2 peer municipios on an outer ring - sidesteps that
        // entirely since positions never depend on edge weight.
        Node focal = null;
        java.util.List<Node> subNodes = new java.util.ArrayList<>();
        java.util.List<Node> peerNodes = new java.util.ArrayList<>();
        for (Node n : graph.getNodes()) {
            String role = String.valueOf(n.getAttribute(roleColumn));
            if (role.equals("focal")) {
                focal = n;
            } else if (role.equals("substance")) {
                subNodes.add(n);
            } else {
                peerNodes.add(n);
            }
        }
        java.util.Comparator<Node> byTotalDesc = java.util.Comparator.comparingDouble(
                (Node n) -> ((Number) n.getAttribute(totalKgColumn)).doubleValue()).reversed();
        subNodes.sort(byTotalDesc);
        peerNodes.sort(byTotalDesc);

        boolean useFa2 = args.length > 2 && args[2].equals("fa2");
        String suffix = useFa2 ? "_fa2" : "";

        if (useFa2) {
            // ForceAtlas2 with edge weights IGNORED (influence 0): the earlier collapse
            // came from Altamira/Bioxido de carbono weights ~1000x the rest.
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
            focal.setX(0f);
            focal.setY(0f);
            float r1 = 500f;
            for (int i = 0; i < subNodes.size(); i++) {
                double angle = 2 * Math.PI * i / subNodes.size();
                subNodes.get(i).setX((float) (r1 * Math.cos(angle)));
                subNodes.get(i).setY((float) (r1 * Math.sin(angle)));
            }
            float r2 = 1000f;
            for (int i = 0; i < peerNodes.size(); i++) {
                double angle = 2 * Math.PI * i / peerNodes.size() + Math.PI / peerNodes.size();
                peerNodes.get(i).setX((float) (r2 * Math.cos(angle)));
                peerNodes.get(i).setY((float) (r2 * Math.sin(angle)));
            }
        }

        AppearanceController appearanceController = Lookup.getDefault().lookup(AppearanceController.class);
        AppearanceModel appearanceModel = appearanceController.getModel(workspace);

        Function partitionFunction = appearanceModel.getNodeFunction(roleColumn, PartitionElementColorTransformer.class);
        Partition partition = ((PartitionFunction) partitionFunction).getPartition();
        for (Object value : partition.getValues(graph)) {
            String v = String.valueOf(value);
            Color color;
            if (v.equals("focal")) {
                color = new Color(0xe3, 0x49, 0x48); // red - the ego
            } else if (v.equals("substance")) {
                color = new Color(0xeb, 0x68, 0x34); // orange
            } else {
                color = new Color(0x2a, 0x78, 0xd6); // blue - peer municipios
            }
            partition.setColor(value, color);
        }
        appearanceController.transform(partitionFunction);

        Function sizeFunction = appearanceModel.getNodeFunction(totalKgColumn, RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer sizeTransformer = (RankingNodeSizeTransformer) sizeFunction.getTransformer();
        sizeTransformer.setMinSize(10);
        sizeTransformer.setMaxSize(40);
        appearanceController.transform(sizeFunction);

        for (Edge e : graph.getEdges()) {
            e.setColor(new Color(0x89, 0x87, 0x81, 140));
        }

        PreviewController previewController = Lookup.getDefault().lookup(PreviewController.class);
        PreviewModel previewModel = previewController.getModel(workspace);
        previewModel.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_FONT, new Font("Arial", Font.PLAIN, 12));
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_SHOW_BOX, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_OPACITY, 92f);
        previewModel.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.8f);
        previewModel.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, new Color(0xfc, 0xfc, 0xfb));
        previewModel.getProperties().putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 65f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, 1.4f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);

        File gexfOut = new File(outDir, "ego_altamira_toolkit" + suffix + ".gexf");
        exportController.exportFile(gexfOut);
        System.out.println("Written " + gexfOut.getAbsolutePath());

        File pdfOut = new File(outDir, "ego_altamira_toolkit" + suffix + ".pdf");
        exportController.exportFile(pdfOut);
        System.out.println("Written " + pdfOut.getAbsolutePath());

        try {
            File pngOut = new File(outDir, "ego_altamira_toolkit" + suffix + ".png");
            org.gephi.io.exporter.preview.PNGExporter pngExporter =
                    (org.gephi.io.exporter.preview.PNGExporter) exportController.getExporter("png");
            pngExporter.setWorkspace(workspace);
            pngExporter.setWidth(1400);
            pngExporter.setHeight(1200);
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
