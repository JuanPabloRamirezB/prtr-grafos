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

/** args: input.gexf outDir */
public class GephiTamaulipas {

    private static Column findColumnByTitle(Table table, String title) {
        for (Column c : table) {
            if (c.getTitle().equalsIgnoreCase(title)) {
                return c;
            }
        }
        throw new IllegalStateException("No column titled '" + title + "' found");
    }

    public static void main(String[] args) throws Exception {
        // PNGExporter needs a real GraphicsEnvironment (G2D render target), so this
        // stays non-headless; we're invoking a real Windows JVM, which has one even
        // with no window ever shown.
        String inputGexf = args.length > 0 ? args[0] : "tamaulipas.gexf";
        String outDir = args.length > 1 ? args[1] : ".";

        // 1. Project + workspace
        ProjectController pc = Lookup.getDefault().lookup(ProjectController.class);
        pc.newProject();
        Workspace workspace = pc.getCurrentWorkspace();

        // 2. Import GEXF
        ImportController importController = Lookup.getDefault().lookup(ImportController.class);
        Container container = importController.importFile(new File(inputGexf));
        container.getLoader().setEdgeDefault(EdgeDirectionDefault.UNDIRECTED);
        container.getLoader().setAllowAutoNode(false);
        importController.process(container, new DefaultProcessor(), workspace);

        GraphModel graphModel = Lookup.getDefault().lookup(GraphController.class).getGraphModel(workspace);
        Graph graph = graphModel.getUndirectedGraph();
        System.out.println("Imported nodes=" + graph.getNodeCount() + " edges=" + graph.getEdgeCount());

        Table nodeTable = graphModel.getNodeTable();
        // NetworkX's GEXF writer stores the GEXF attribute id ("0", "1", ...) as the
        // Gephi column id; the readable name only survives as the column title.
        Column typeColumn = findColumnByTitle(nodeTable, "type");
        Column totalKgColumn = findColumnByTitle(nodeTable, "total_kg");

        // 3. Layout - a real force-directed layout (ForceAtlas2) collapses this graph:
        // it's dense and bipartite (many substances connect to nearly every location),
        // so most nodes pile on the same spot with one or two flung far away (confirmed
        // both here and with networkx's spring_layout in the Python version). A
        // two-column bipartite layout - locations left, substances right, each ranked
        // by total emissions - is what actually stays readable for this shape of data.
        List<Node> locNodes = new ArrayList<>();
        List<Node> subNodes = new ArrayList<>();
        for (Node n : graph.getNodes()) {
            String kind = String.valueOf(n.getAttribute(typeColumn));
            (kind.equals("location") ? locNodes : subNodes).add(n);
        }
        Comparator<Node> byTotalDesc = Comparator.comparingDouble(
                (Node n) -> ((Number) n.getAttribute(totalKgColumn)).doubleValue()).reversed();
        locNodes.sort(byTotalDesc);
        subNodes.sort(byTotalDesc);

        // Both columns span the same total height regardless of node count, so a
        // 20-row column and a 71-row column line up instead of leaving one column's
        // export bounding box mostly empty.
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

        // 4. Appearance - color by node type (location/substance), size by total_kg
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

        Function sizeFunction = appearanceModel.getNodeFunction(totalKgColumn, RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer sizeTransformer = (RankingNodeSizeTransformer) sizeFunction.getTransformer();
        sizeTransformer.setMinSize(6);
        sizeTransformer.setMaxSize(55);
        appearanceController.transform(sizeFunction);

        // Edge color: light gray, so labels/nodes stay legible
        for (Edge e : graph.getEdges()) {
            e.setColor(new Color(0x89, 0x87, 0x81, 90));
        }

        // 5. Preview settings
        PreviewController previewController = Lookup.getDefault().lookup(PreviewController.class);
        PreviewModel previewModel = previewController.getModel(workspace);
        previewModel.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_FONT, new Font("Arial", Font.PLAIN, 10));
        previewModel.getProperties().putValue(PreviewProperty.NODE_LABEL_SHOW_BOX, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.NODE_OPACITY, 90f);
        previewModel.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.6f);
        previewModel.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, new Color(0xfc, 0xfc, 0xfb));
        previewModel.getProperties().putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 55f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, 1.2f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

        // 7. Export: laid-out GEXF (reopen in desktop Gephi) + PDF + PNG
        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);

        File gexfOut = new File(outDir, "tamaulipas_graph_toolkit_layout.gexf");
        exportController.exportFile(gexfOut);
        System.out.println("Written " + gexfOut.getAbsolutePath());

        File pdfOut = new File(outDir, "tamaulipas_graph_toolkit.pdf");
        exportController.exportFile(pdfOut);
        System.out.println("Written " + pdfOut.getAbsolutePath());

        try {
            File pngOut = new File(outDir, "tamaulipas_graph_toolkit.png");
            org.gephi.io.exporter.preview.PNGExporter pngExporter =
                    (org.gephi.io.exporter.preview.PNGExporter) exportController.getExporter("png");
            pngExporter.setWorkspace(workspace);
            pngExporter.setWidth(1400);
            pngExporter.setHeight(2600);
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
