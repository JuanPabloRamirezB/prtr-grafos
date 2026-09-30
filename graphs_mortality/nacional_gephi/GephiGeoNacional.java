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

/** Municipio-similarity network positioned at REAL lat/lon coordinates
 * instead of a force-directed layout - a "geographic layout" done by hand
 * (set X/Y from real coordinates) since the Gephi Toolkit's -all jar does
 * not bundle the third-party GeoLayout plugin. */
/** args: input.gexf outDir   (node attributes lat, lon, total_kg; communities from Gephi Modularity) */
public class GephiGeoNacional {

    private static final String[] CAT_COLORS = {
        "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"
    };

    private static Column findColumnByTitle(Table table, String title) {
        for (Column c : table) {
            if (c.getTitle().equalsIgnoreCase(title)) {
                return c;
            }
        }
        throw new IllegalStateException("No column titled '" + title + "' found");
    }

    public static void main(String[] args) throws Exception {
        String inputGexf = args.length > 0 ? args[0] : "municipio_geo.gexf";
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
        org.gephi.statistics.plugin.Modularity mod = new org.gephi.statistics.plugin.Modularity();
        mod.setUseWeight(true);
        mod.setResolution(1.0);
        mod.execute(graphModel);
        System.out.println("Modularity=" + mod.getModularity());

        Table nodeTable = graphModel.getNodeTable();
        Column latColumn = findColumnByTitle(nodeTable, "lat");
        Column lonColumn = findColumnByTitle(nodeTable, "lon");
        Column totalKgColumn = findColumnByTitle(nodeTable, "total_kg");
        Column communityColumn = findColumnByTitle(nodeTable, "Modularity Class");

        // Position = real geography, longitude scaled by cos(mean latitude) so the
        // east-west spread isn't stretched relative to north-south (a crude
        // equirectangular correction - Tamaulipas is narrow enough this is plenty).
        // Raw lat/lon*scale left everything offset tens of thousands of units from
        // the origin (lat ~22-27 -> y ~88000-110000): the PNG/PDF preview exporter
        // does not auto-fit that to the canvas the way it did for our other,
        // origin-centered graphs, so it rendered as a speck in one corner. Centering
        // on the centroid and scaling to a fixed target span fixes it and matches
        // the coordinate magnitudes every other concept here already uses.
        double meanLat = Math.toRadians(23.5);
        double latSum = 0, lonSum = 0;
        int n = 0;
        for (Node node : graph.getNodes()) {
            latSum += ((Number) node.getAttribute(latColumn)).doubleValue();
            lonSum += ((Number) node.getAttribute(lonColumn)).doubleValue();
            n++;
        }
        double latCenter = latSum / n, lonCenter = lonSum / n;

        double maxExtent = 1e-9;
        for (Node node : graph.getNodes()) {
            double lat = ((Number) node.getAttribute(latColumn)).doubleValue();
            double lon = ((Number) node.getAttribute(lonColumn)).doubleValue();
            double dy = lat - latCenter;
            double dx = (lon - lonCenter) * Math.cos(meanLat);
            maxExtent = Math.max(maxExtent, Math.max(Math.abs(dx), Math.abs(dy)));
        }
        float targetHalfSpan = 1000f;
        float scale = (float) (targetHalfSpan / maxExtent);
        for (Node node : graph.getNodes()) {
            double lat = ((Number) node.getAttribute(latColumn)).doubleValue();
            double lon = ((Number) node.getAttribute(lonColumn)).doubleValue();
            node.setY((float) ((lat - latCenter) * scale));
            node.setX((float) ((lon - lonCenter) * Math.cos(meanLat) * scale));
        }

        AppearanceController appearanceController = Lookup.getDefault().lookup(AppearanceController.class);
        AppearanceModel appearanceModel = appearanceController.getModel(workspace);

        Function partitionFunction = appearanceModel.getNodeFunction(communityColumn, PartitionElementColorTransformer.class);
        Partition partition = ((PartitionFunction) partitionFunction).getPartition();
        for (Object value : partition.getValues(graph)) {
            int idx = ((Number) value).intValue();
            partition.setColor(value, Color.decode(CAT_COLORS[idx % CAT_COLORS.length]));
        }
        appearanceController.transform(partitionFunction);

        Function sizeFunction = appearanceModel.getNodeFunction(totalKgColumn, RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer sizeTransformer = (RankingNodeSizeTransformer) sizeFunction.getTransformer();
        sizeTransformer.setMinSize(14);
        sizeTransformer.setMaxSize(50);
        appearanceController.transform(sizeFunction);

        for (Edge e : graph.getEdges()) {
            e.setColor(new Color(0x89, 0x87, 0x81, 130));
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
        previewModel.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 60f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, 1.4f);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
        previewModel.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);

        File gexfOut = new File(outDir, "estado_geo_toolkit.gexf");
        exportController.exportFile(gexfOut);
        System.out.println("Written " + gexfOut.getAbsolutePath());

        File pdfOut = new File(outDir, "estado_geo_toolkit.pdf");
        exportController.exportFile(pdfOut);
        System.out.println("Written " + pdfOut.getAbsolutePath());

        try {
            File pngOut = new File(outDir, "estado_geo_toolkit.png");
            org.gephi.io.exporter.preview.PNGExporter pngExporter =
                    (org.gephi.io.exporter.preview.PNGExporter) exportController.getExporter("png");
            pngExporter.setWorkspace(workspace);
            pngExporter.setWidth(2000);
            pngExporter.setHeight(1300);
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
