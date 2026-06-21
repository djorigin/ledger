import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listProjects } from "@/api/projects";
import { useAuth } from "@/auth/AuthContext";
import { ProjectForm } from "@/components/projects/ProjectForm";
import { ProjectList } from "@/components/projects/ProjectList";

export function ProjectsPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const { user } = useAuth();

  const projectsQuery = useQuery({
    queryKey: ["projects", entityId],
    queryFn: () => listProjects(entityId),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  if (projectsQuery.isLoading) return <p className="text-muted-foreground">Loading…</p>;

  const projects = projectsQuery.data?.results ?? [];
  const role = user?.memberships.find((m) => m.entity_id === entityId)?.role;
  const canEdit = role === "EDITOR" || role === "OWNER";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Projects</h1>
      {canEdit && <ProjectForm entityId={entityId} />}
      <ProjectList projects={projects} />
    </div>
  );
}
