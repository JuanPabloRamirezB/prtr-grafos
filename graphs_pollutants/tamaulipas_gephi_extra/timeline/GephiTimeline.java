import java.awt.Color;
import java.awt.Font;
import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import org.gephi.appearance.api.AppearanceController;
import org.gephi.appearance.api.AppearanceModel;
import org.gephi.appearance.api.Function;
import org.gephi.appearance.plugin.RankingElementColorTransformer;
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

/** Static "temporal fingerprint" of the Tamaulipas bipartite graph: color =
 * first year a node reported (sequential blue ramp, light=recent newcomer,
 * dark=reporting since early in the series), size = how many distinct years
 * it has reported (longevity/consistency). The full year-by-year animation
 * lives in ../../tamaulipas_temporal_graph/ - this is the single-frame,
 * Gephi-rendered companion view. */
/** args: input.gexf outDir [fa2]   (fa2 = ForceAtlas2 layout instead of two columns; outputs get the suffix _fa2) */
public class GephiTimeline {

    private static Column findColumnByTitle(Table table, String title) {
        for (Column c : table) {
            if (c.getTitle().equalsIgnoreCase(title)) {
                return c;
            }
        }
        throw new IllegalStateException("No column titled '" + title + "' found");
    }

    public static void main(String[] args) throws Exception {
        String inputGexf = args.length > 0 ? args[0] : "temporal_fingerprint.gexf";
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
        Column typeColumn = findColumnByTitle(nodeTable, "type");
        Column firstYearColumn = findColumnByTitle(nodeTable, "first_year");
        Column nYearsColumn = findColumnByTitle(nodeTable, "n_years_active");

        List<Node> locNodes = new ArrayList<>();
        List<Node> subNodes = new ArrayList<>();
        for (Node n : graph.getNodes()) {
            String kind = String.valueOf(n.getAttribute(typeColumn));
            (kind.equals("location") ? locNodes : subNodes).add(n);
        }
        Comparator<Node> byFirstYearThenYears = Comparator
                .comparingInt((Node n) -> ((Number) n.getAttribute(firstYearColumn)).intValue())
                .thenComparing(Comparator.comparingInt(
                        (Node n) -> ((Number) n.getAttribute(nYearsColumn)).intValue()).reversed());
        locNodes.sort(byFirstYearThenYears);
        subNodes.sort(byFirstYearThenYears);

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

        // Sequential ramp (dataviz palette): light blue = recent first-report,
        // dark blue = reporting since early in the 2004-2022 series.
        Function colorFunction = appearanceModel.getNodeFunction(firstYearColumn, RankingElementColorTransformer.class);
        RankingElementColorTransformer colorTransformer = (RankingElementColorTransformer) colorFunction.getTransformer();
        colorTransformer.setColors(new Color[]{
            Color.decode("#cde2fb"), Color.decode("#5598e7"), Color.decode("#184f95")
        });
        appearanceController.transform(colorFunction);

        Function sizeFunction = appearanceModel.getNodeFunction(nYearsColumn, RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer sizeTransformer = (RankingNodeSizeTransformer) sizeFunction.getTransformer();
        sizeTransformer.setMinSize(6);
        sizeTransformer.setMaxSize(50);
        appearanceController.transform(sizeFunction);

        for (Edge e : graph.getEdges()) {
            e.setColor(new Color(0x89, 0x87, 0x81, 90));
        }

        PreviewController previewController = Lookup.getDefault().lookup(PreviewController.class);
        PreviewModel previewModel = previewController.getModel(workspace);
        previewModel.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_FONT, new Font("Arial", Font.PLAIN, 10));
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_SHOW_BOX, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_OPACITY, 92f);
        previewModel.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.6f);
        previewModel.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, new Color(0xfc, 0xfc, 0xfb));
        previewModel.getProperties().putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 55f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, 1.2f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);

        File gexfOut = new File(outDir, "timeline_toolkit" + suffix + ".gexf");
        exportController.exportFile(gexfOut);
        System.out.println("Written " + gexfOut.getAbsolutePath());

        File pdfOut = new File(outDir, "timeline_toolkit" + suffix + ".pdf");
        exportController.exportFile(pdfOut);
        System.out.println("Written " + pdfOut.getAbsolutePath());

        try {
            File pngOut = new File(outDir, "timeline_toolkit" + suffix + ".png");
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
