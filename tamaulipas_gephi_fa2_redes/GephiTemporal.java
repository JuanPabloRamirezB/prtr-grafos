import java.awt.Color;
import java.awt.Font;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

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

/** Temporal Municipio<->Sustancia graph. ForceAtlas2 runs ONCE on the union of
 * all years (edge weight influence 0); those positions are then reused for
 * every year so nodes never jump between frames. Per year: edges absent that
 * year are removed, node size = that year's Kg (log scale, bounds fixed across
 * all years so sizes are comparable between frames), inactive nodes are tiny
 * gray dots. PNG for every year, PDF for the snapshot years.
 * args: union.gexf outDir years(csv) pdfYears(csv) */
public class GephiTemporal {

    private static Column col(Table t, String title) {
        for (Column c : t) {
            if (c.getTitle().equalsIgnoreCase(title)) {
                return c;
            }
        }
        throw new IllegalStateException("No column " + title);
    }

    private static Workspace load(String gexf, ProjectController pc) throws Exception {
        pc.newProject();
        Workspace ws = pc.getCurrentWorkspace();
        ImportController ic = Lookup.getDefault().lookup(ImportController.class);
        Container container = ic.importFile(new File(gexf));
        container.getLoader().setEdgeDefault(EdgeDirectionDefault.UNDIRECTED);
        container.getLoader().setAllowAutoNode(false);
        ic.process(container, new DefaultProcessor(), ws);
        return ws;
    }

    public static void main(String[] args) throws Exception {
        String gexf = args[0];
        String outDir = args[1];
        String[] years = args[2].split(",");
        java.util.Set<String> pdfYears = new java.util.HashSet<>(java.util.Arrays.asList(args[3].split(",")));

        ProjectController pc = Lookup.getDefault().lookup(ProjectController.class);
        ExportController ec = Lookup.getDefault().lookup(ExportController.class);

        // ---- 1. ForceAtlas2 once, on the union graph
        Workspace ws = load(gexf, pc);
        GraphModel gm = Lookup.getDefault().lookup(GraphController.class).getGraphModel(ws);
        Graph g = gm.getUndirectedGraph();
        ForceAtlas2 layout = new ForceAtlas2Builder().buildLayout();
        layout.setGraphModel(gm);
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
        System.out.println("FA2 ran " + steps + " steps on union graph");

        Map<String, float[]> pos = new HashMap<>();
        Map<String, String> labels = new HashMap<>();
        Column labelCol = col(gm.getNodeTable(), "Label");
        for (Node n : g.getNodes()) {
            pos.put(String.valueOf(n.getId()), new float[]{n.x(), n.y()});
        }
        ec.exportFile(new File(outDir, "temporal_union_fa2.gexf"));

        // ---- 2. Global log-scale bounds of per-node yearly Kg (>0), fixed across frames
        double gmin = Double.MAX_VALUE, gmax = 0;
        Table nt = gm.getNodeTable();
        for (Node n : g.getNodes()) {
            for (String y : years) {
                double v = ((Number) n.getAttribute(col(nt, "kg_" + y))).doubleValue();
                if (v > 0) {
                    gmin = Math.min(gmin, v);
                    gmax = Math.max(gmax, v);
                }
            }
        }
        System.out.println("kg range " + gmin + " .. " + gmax);

        // ---- 3. One render per year with the shared positions
        for (String y : years) {
            Workspace w = load(gexf, pc);
            GraphModel m = Lookup.getDefault().lookup(GraphController.class).getGraphModel(w);
            Graph graph = m.getUndirectedGraph();
            Table nodeT = m.getNodeTable();
            Table edgeT = m.getEdgeTable();
            Column kgY = col(nodeT, "kg_" + y);
            Column type = col(nodeT, "type");
            Column eY = col(edgeT, "y_" + y);

            List<Edge> drop = new ArrayList<>();
            for (Edge e : graph.getEdges()) {
                if (((Number) e.getAttribute(eY)).doubleValue() <= 0) {
                    drop.add(e);
                }
            }
            for (Edge e : drop) {
                graph.removeEdge(e);
            }
            for (Edge e : graph.getEdges()) {
                e.setColor(new Color(0x89, 0x87, 0x81, 110));
            }
            double totalYear = 0;
            for (Node n : graph.getNodes()) {
                float[] p = pos.get(String.valueOf(n.getId()));
                n.setX(p[0]);
                n.setY(p[1]);
                double v = ((Number) n.getAttribute(kgY)).doubleValue();
                boolean loc = String.valueOf(n.getAttribute(type)).equals("location");
                if (loc) {
                    totalYear += v;
                }
                if (v > 0) {
                    double t = (Math.log1p(v) - Math.log1p(gmin)) / (Math.log1p(gmax) - Math.log1p(gmin));
                    n.setSize((float) (6 + Math.max(0, Math.min(1, t)) * 40));
                    n.setColor(loc ? new Color(0x2a, 0x78, 0xd6) : new Color(0xeb, 0x68, 0x34));
                } else {
                    n.setSize(4f);
                    n.setColor(new Color(0xc3, 0xc2, 0xb7));
                    n.setLabel("");
                }
            }

            PreviewController prc = Lookup.getDefault().lookup(PreviewController.class);
            PreviewModel pm = prc.getModel(w);
            pm.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
            pm.getProperties().putValue(PreviewProperty.NODE_LABEL_FONT, new Font("Arial", Font.PLAIN, 10));
            pm.getProperties().putValue(PreviewProperty.NODE_LABEL_SHOW_BOX, Boolean.FALSE);
            pm.getProperties().putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
            pm.getProperties().putValue(PreviewProperty.NODE_OPACITY, 92f);
            pm.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.6f);
            pm.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, new Color(0xfc, 0xfc, 0xfb));
            pm.getProperties().putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
            pm.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 55f);
            pm.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, 1.2f);
            pm.getProperties().putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
            pm.getProperties().putValue(PreviewProperty.EDGE_COLOR,
                    new org.gephi.preview.types.EdgeColor(org.gephi.preview.types.EdgeColor.Mode.MIXED));

            File framesDir = new File(outDir, "frames");
            framesDir.mkdirs();
            org.gephi.io.exporter.preview.PNGExporter png =
                    (org.gephi.io.exporter.preview.PNGExporter) ec.getExporter("png");
            png.setWorkspace(w);
            png.setWidth(1400);
            png.setHeight(1200);
            png.setTransparentBackground(false);
            ec.exportFile(new File(framesDir, "temporal_" + y + ".png"), png);
            if (pdfYears.contains(y)) {
                ec.exportFile(new File(outDir, "temporal_" + y + "_fa2.pdf"));
            }
            System.out.println("frame " + y + "  edges=" + graph.getEdgeCount()
                    + "  total_kg(municipios)=" + String.format("%.0f", totalYear));
        }
        System.out.println("DONE");
    }
}
