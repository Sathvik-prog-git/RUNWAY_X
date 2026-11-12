import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

/** Titled glowing card. `icon` is a lucide component; `viewAll` is a route. */
export default function Panel({ title, icon: Icon, viewAll, action, className = "", children }) {
  return (
    <section className={`panel p-5 ${className}`}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-3 text-base font-semibold">
          {Icon && <Icon className="h-5 w-5 text-brand-sky" />}
          {title}
        </h2>
        {viewAll && (
          <Link to={viewAll} className="link-accent flex items-center gap-1">
            View All <ArrowRight className="h-4 w-4" />
          </Link>
        )}
        {action}
      </div>
      {children}
    </section>
  );
}
