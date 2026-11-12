import { Construction } from "lucide-react";
import Panel from "../components/ui/Panel.jsx";

/** Stand-in for every route that has no real page yet. */
export default function PlaceholderPage({ title }) {
  const file = `src/pages/${title.replace(/\s+/g, "")}Page.jsx`;
  return (
    <Panel title={title} icon={Construction} className="max-w-xl">
      <p className="text-sm text-slate-300">
        This page isn't built yet. Create <code className="text-brand-sky">{file}</code> and
        point this route at it in <code className="text-brand-sky">App.jsx</code>.
      </p>
    </Panel>
  );
}
