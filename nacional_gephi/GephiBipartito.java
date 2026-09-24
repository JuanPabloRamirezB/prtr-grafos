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
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2;
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2Builder;
import org.gephi.preview.api.PreviewController;
import org.gephi.preview.api.PreviewModel;
import org.gephi.preview.api.PreviewProperty;
import org.gephi.project.api.ProjectController;
import org.gephi.project.api.Workspace;
import org.openide.util.Lookup;

/** National bipartite graph (Estado or Municipio <-> Sustancia) with ForceAtlas2
 * (edge weight influence 0 - a handful of huge emitters otherwise collapse it).
 * Labels are kept only for the topLabels nodes by total_kg (the rest are blanked
 * in the render; hover text in the HTML is built from the source GEXF instead).
 * args: input outDir base scaling gravity steps maxSize topLabels edgeAlpha edgeThickness width height [sizeColumnTitle] */
public class GephiBipartito {

    private static Column findColumn(Table t, String title) {
        for (Column c : t) {
            if (c.getTitle().equalsIgnoreCase(title)) {
                return c;
            }
        }
        throw new IllegalStateException("No column " + title);
    }

    public static void main(String[] args) throws Exception {
        String input = args[0], outDir = args[1], base = args[2];
        double scaling = Double.parseDouble(args[3]);
        double gravity = Double.parseDouble(args[4]);
        int maxSteps = Integer.parseInt(args[5]);
        double maxSize = Double.parseDouble(args[6]);
        int topLabels = Integer.parseInt(args[7]);
        int edgeAlpha = Integer.parseInt(args[8]);
        float edgeThickness = Float.parseFloat(args[9]);
        int width = Integer.parseInt(args[10]), height = Integer.parseInt(args[11]);
        String sizeTitle = args.length > 12 ? args[12] : "total_kg";

        ProjectController pc = Lookup.getDefault().lookup(ProjectController.class);
        pc.newProject();
        Workspace workspace = pc.getCurrentWorkspace();
        ImportController ic = Lookup.getDefault().lookup(ImportController.class);
        Container container = ic.importFile(new File(input));
        container.getLoader().setEdgeDefault(EdgeDirectionDefault.UNDIRECTED);
        container.getLoader().setAllowAutoNode(false);
        ic.process(container, new DefaultProcessor(), workspace);

        GraphModel gm = Lookup.getDefault().lookup(GraphController.class).getGraphModel(workspace);
        Graph graph = gm.getUndirectedGraph();
        System.out.println("Imported nodes=" + graph.getNodeCount() + " edges=" + graph.getEdgeCount());
        Table nt = gm.getNodeTable();
        Column type = findColumn(nt, "type");
        Column total = findColumn(nt, "total_kg");

        ForceAtlas2 layout = new ForceAtlas2Builder().buildLayout();
        layout.setGraphModel(gm);
        layout.resetPropertiesValues();
        layout.setEdgeWeightInfluence(0.0);
        layout.setScalingRatio(scaling);
        layout.setGravity(gravity);
        layout.setOutboundAttractionDistribution(true);
        layout.setAdjustSizes(true);
        layout.setJitterTolerance(1.0);
        layout.setBarnesHutOptimize(graph.getNodeCount() > 300);
        layout.initAlgo();
        int steps = 0;
        while (layout.canAlgo() && steps < maxSteps) {
            layout.goAlgo();
            steps++;
        }
        layout.endAlgo();
        System.out.println("FA2 ran " + steps + " steps");

        AppearanceController ac = Lookup.getDefault().lookup(AppearanceController.class);
        AppearanceModel am = ac.getModel(workspace);
        Function pf = am.getNodeFunction(type, PartitionElementColorTransformer.class);
        Partition partition = ((PartitionFunction) pf).getPartition();
        for (Object value : partition.getValues(graph)) {
            partition.setColor(value, String.valueOf(value).equals("location")
                    ? new Color(0x2a, 0x78, 0xd6) : new Color(0xeb, 0x68, 0x34));
        }
        ac.transform(pf);
        Function sf = am.getNodeFunction(findColumn(nt, sizeTitle), RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer st = (RankingNodeSizeTransformer) sf.getTransformer();
        st.setMinSize((float) (maxSize * 0.2));
        st.setMaxSize((float) maxSize);
        ac.transform(sf);
        for (Edge e : graph.getEdges()) {
            e.setColor(new Color(0x89, 0x87, 0x81, edgeAlpha));
        }

        List<Node> byTotal = new ArrayList<>();
        for (Node n : graph.getNodes()) {
            byTotal.add(n);
        }
        byTotal.sort(Comparator.comparingDouble((Node n) -> ((Number) n.getAttribute(total)).doubleValue()).reversed());
        for (int i = topLabels; i < byTotal.size(); i++) {
            byTotal.get(i).setLabel("");
        }

        PreviewController pvc = Lookup.getDefault().lookup(PreviewController.class);
        PreviewModel pm = pvc.getModel(workspace);
        pm.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
        pm.getProperties().putValue(PreviewProperty.NODE_LABEL_FONT, new Font("Arial", Font.PLAIN, 12));
        pm.getProperties().putValue(PreviewProperty.NODE_LABEL_SHOW_BOX, Boolean.FALSE);
        pm.getProperties().putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
        pm.getProperties().putValue(PreviewProperty.NODE_OPACITY, 92f);
        pm.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.6f);
        pm.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, new Color(0xfc, 0xfc, 0xfb));
        pm.getProperties().putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
        pm.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 60f);
        pm.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, edgeThickness);
        pm.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
        pm.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

        ExportController ec = Lookup.getDefault().lookup(ExportController.class);
        ec.exportFile(new File(outDir, base + "_fa2.gexf"));
        ec.exportFile(new File(outDir, base + "_fa2.pdf"));
        org.gephi.io.exporter.preview.PNGExporter png =
                (org.gephi.io.exporter.preview.PNGExporter) ec.getExporter("png");
        png.setWorkspace(workspace);
        png.setWidth(width);
        png.setHeight(height);
        png.setTransparentBackground(false);
        ec.exportFile(new File(outDir, base + "_fa2.png"), png);
        System.out.println("DONE " + base);
    }
}
