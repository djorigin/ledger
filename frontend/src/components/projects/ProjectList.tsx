import { useQuery } from "@tanstack/react-query";

import { getProjectProgress } from "@/api/projects";
import { ProgressBar } from "@/components/ui/progress-bar";
import { formatMoney } from "@/lib/money";
import type { Project } from "@/types/api";

function ProjectRow({ project }: { project: Project }) {
  const progressQuery = useQuery({
    queryKey: ["project-progress", project.id],
    queryFn: () => getProjectProgress(project.id),
  });

  return (
    <div className="space-y-1 rounded border p-3">
      <div className="flex items-center justify-between">
        <span className="font-medium">{project.name}</span>
        <span className="text-xs text-muted-foreground">{project.status}</span>
      </div>
      {project.description && <p className="text-sm text-muted-foreground">{project.description}</p>}
      {progressQuery.data && (
        <>
          <ProgressBar percent={progressQuery.data.percent_used ? Number(progressQuery.data.percent_used) : null} />
          <p className="text-sm text-muted-foreground">
            {formatMoney(progressQuery.data.actual_to_date, project.currency)} of{" "}
            {formatMoney(progressQuery.data.budget_amount, project.currency)} spent
          </p>
        </>
      )}
    </div>
  );
}

interface ProjectListProps {
  projects: Project[];
}

export function ProjectList({ projects }: ProjectListProps) {
  if (projects.length === 0) {
    return <p className="text-muted-foreground">No projects yet.</p>;
  }
  return (
    <div className="space-y-3">
      {projects.map((project) => (
        <ProjectRow key={project.id} project={project} />
      ))}
    </div>
  );
}
