import org.jgroups.*;
import org.jgroups.util.Util;

import java.io.*;
import java.util.*;

public class SimpleChat implements Receiver {
    private JChannel channel;
    private final String user = System.getProperty("user.name", "n/a");
    private final List<String> state = new LinkedList<>();

    private void start() throws Exception {
        channel = new JChannel();          // usa udp.xml padrão do JAR
        channel.setReceiver(this);         // este objeto recebe callbacks
        channel.connect("ChatCluster");    // entra (ou cria) o cluster
        channel.getState(null, 10_000);    // pega histórico, se existir
        eventLoop();
        channel.close();
    }

    /* ============ callbacks ============ */

    @Override
    public void receive(Message msg) {
        String line = msg.getSrc() + ": " + msg.getObject();   // ObjectMessage -> getObject()
        System.out.println(line);
        synchronized (state) { state.add(line); }
    }

    @Override
    public void viewAccepted(View view) { System.out.println("** view: " + view); }

    @Override
    public void getState(OutputStream out) throws Exception {
        synchronized (state) { Util.objectToStream(state, new DataOutputStream(out)); }
    }

    @Override
    public void setState(InputStream in) throws Exception {
        List<String> list = Util.objectFromStream(new DataInputStream(in));
        synchronized (state) { state.clear(); state.addAll(list); }
        System.out.println(list.size() + " past messages:");
        for (String s : list) System.out.println(s);
    }

    /* ============ loop de leitura ============ */

    private void eventLoop() throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        while (true) {
            System.out.print("> "); System.out.flush();
            String line = in.readLine();
            if (line == null) continue;
            if (line.equalsIgnoreCase("quit") || line.equalsIgnoreCase("exit")) break;

            Message msg = new ObjectMessage(null, "[" + user + "] " + line);
            channel.send(msg);
        }
    }

    public static void main(String[] args) throws Exception { new SimpleChat().start(); }
}

