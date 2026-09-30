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
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2;
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2Builder;
import org.gephi.preview.api.PreviewController;
import org.gephi.preview.api.PreviewModel;
import org.gephi.preview.api.PreviewProperty;
import org.gephi.project.api.ProjectController;
import org.gephi.project.api.Workspace;
import org.gephi.statistics.plugin.Modularity;
import org.openide.util.Lookup;

/** One-mode projected network (Sustancia<->Sustancia or Municipio<->Municipio):
 * ForceAtlas2 layout + Gephi's own Modularity for communities.
 * args: input.gexf outDir baseName sizeColumnTitle edgeWeightInfluence scaling [gravity [normal|strong [maxNodeSize [pack]]]]
 * ("pack" re-places disconnected components on a compact grid after ForceAtlas2) */
public class GephiProyectada {

    private static final String[] CAT_COLORS = {
        "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"
    };

    private static Column findColumn(Table table, String needle) {
        for (Column c : table) {
            if (c.getTitle().toLowerCase().contains(needle.toLowerCase())) {
                return c;
            }
        }
        throw new IllegalStateException("No column containing '" + needle + "'");
    }


    /** FA2 has nothing pulling disconnected components together, so it flings them
     * far apart. Keep FA2's layout INSIDE each component, then re-place the
     * components on a compact grid (largest first). */
    private static void packComponents(Graph graph) {
        java.util.Map<Node, Integer> seen = new java.util.HashMap<>();
        java.util.List<java.util.List<Node>> comps = new java.util.ArrayList<>();
        for (Node n : graph.getNodes()) {
            if (seen.containsKey(n)) {
                continue;
            }
            java.util.List<Node> members = new java.util.ArrayList<>();
            java.util.ArrayDeque<Node> queue = new java.util.ArrayDeque<>();
            queue.add(n);
            seen.put(n, comps.size());
            while (!queue.isEmpty()) {
                Node c = queue.poll();
                members.add(c);
                for (Node nb : graph.getNeighbors(c)) {
                    if (!seen.containsKey(nb)) {
                        seen.put(nb, comps.size());
                        queue.add(nb);
                    }
                }
            }
            comps.add(members);
        }
        comps.sort((a, b) -> b.size() - a.size());
        int k = comps.size();
        float[] cx = new float[k], cy = new float[k], w = new float[k], h = new float[k];
        float maxDim = 1f;
        for (int i = 0; i < k; i++) {
            float minX = Float.MAX_VALUE, maxX = -Float.MAX_VALUE, minY = Float.MAX_VALUE, maxY = -Float.MAX_VALUE;
            for (Node n : comps.get(i)) {
                minX = Math.min(minX, n.x()); maxX = Math.max(maxX, n.x());
                minY = Math.min(minY, n.y()); maxY = Math.max(maxY, n.y());
            }
            cx[i] = (minX + maxX) / 2; cy[i] = (minY + maxY) / 2;
            w[i] = maxX - minX; h[i] = maxY - minY;
            maxDim = Math.max(maxDim, Math.max(w[i], h[i]));
        }
        float gap = 0.3f * maxDim;
        int cols = (int) Math.ceil(Math.sqrt(k));
        float[] colW = new float[cols];
        float[] rowH = new float[(k + cols - 1) / cols];
        for (int i = 0; i < k; i++) {
            colW[i % cols] = Math.max(colW[i % cols], w[i]);
            rowH[i / cols] = Math.max(rowH[i / cols], h[i]);
        }
        float[] colX = new float[cols], rowY = new float[rowH.length];
        float acc = 0;
        for (int c = 0; c < cols; c++) { colX[c] = acc + colW[c] / 2; acc += colW[c] + gap; }
        acc = 0;
        for (int r = 0; r < rowH.length; r++) { rowY[r] = acc + rowH[r] / 2; acc += rowH[r] + gap; }
        for (int i = 0; i < k; i++) {
            float tx = colX[i % cols], ty = rowY[i / cols];
            for (Node n : comps.get(i)) {
                n.setX(n.x() - cx[i] + tx);
                n.setY(n.y() - cy[i] + ty);
            }
        }
    }

    public static void main(String[] args) throws Exception {
        String inputGexf = args[0];
        String outDir = args[1];
        String base = args[2];
        String sizeCol = args[3];
        double weightInfluence = Double.parseDouble(args[4]);
        double scaling = Double.parseDouble(args[5]);

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

        // Communities from Gephi's own Modularity (weighted)
        Modularity modularity = new Modularity();
        modularity.setUseWeight(true);
        modularity.setResolution(1.0);
        modularity.execute(graphModel);
        System.out.println("Modularity=" + modularity.getModularity());

        Table nodeTable = graphModel.getNodeTable();
        Column modClass = findColumn(nodeTable, "modularity");
        Column sizeColumn = findColumn(nodeTable, sizeCol);

        ForceAtlas2 layout = new ForceAtlas2Builder().buildLayout();
        layout.setGraphModel(graphModel);
        layout.resetPropertiesValues();
        layout.setEdgeWeightInfluence(weightInfluence);
        layout.setScalingRatio(scaling);
        double gravity = args.length > 6 ? Double.parseDouble(args[6]) : 1.0;
        layout.setGravity(gravity);
        layout.setStrongGravityMode(args.length > 7 && args[7].equals("strong"));
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
        if (args.length > 9 && args[9].equals("pack")) {
            packComponents(graph);
        }

        AppearanceController appearanceController = Lookup.getDefault().lookup(AppearanceController.class);
        AppearanceModel appearanceModel = appearanceController.getModel(workspace);

        Function partitionFunction = appearanceModel.getNodeFunction(modClass, PartitionElementColorTransformer.class);
        Partition partition = ((PartitionFunction) partitionFunction).getPartition();
        for (Object value : partition.getValues(graph)) {
            int idx = ((Number) value).intValue();
            partition.setColor(value, Color.decode(CAT_COLORS[idx % CAT_COLORS.length]));
        }
        appearanceController.transform(partitionFunction);

        Function sizeFunction = appearanceModel.getNodeFunction(sizeColumn, RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer sizeTransformer = (RankingNodeSizeTransformer) sizeFunction.getTransformer();
        double maxSize = args.length > 8 ? Double.parseDouble(args[8]) : 45;
        sizeTransformer.setMinSize((float) (maxSize * 0.27));
        sizeTransformer.setMaxSize((float) maxSize);
        appearanceController.transform(sizeFunction);

        for (Edge e : graph.getEdges()) {
            e.setColor(new Color(0x89, 0x87, 0x81, 120));
        }

        PreviewController previewController = Lookup.getDefault().lookup(PreviewController.class);
        PreviewModel previewModel = previewController.getModel(workspace);
        previewModel.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_FONT, new Font("Arial", Font.PLAIN, 11));
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_SHOW_BOX, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_OPACITY, 92f);
        previewModel.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.8f);
        previewModel.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, new Color(0xfc, 0xfc, 0xfb));
        previewModel.getProperties().putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 60f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, 1.4f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);
        exportController.exportFile(new File(outDir, base + "_fa2.gexf"));
        exportController.exportFile(new File(outDir, base + "_fa2.pdf"));
        org.gephi.io.exporter.preview.PNGExporter png =
                (org.gephi.io.exporter.preview.PNGExporter) exportController.getExporter("png");
        png.setWorkspace(workspace);
        png.setWidth(1800);
        png.setHeight(1600);
        png.setTransparentBackground(false);
        exportController.exportFile(new File(outDir, base + "_fa2.png"), png);
        System.out.println("DONE " + base);
    }
}
