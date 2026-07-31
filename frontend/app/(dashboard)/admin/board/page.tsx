"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Clock, LayoutGrid } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { cn } from "@/lib/utils";
import { KANBAN_COLUMNS, type KanbanBoard, type Task, type TaskStatus } from "@/lib/types";

function useBoard() {
  return useQuery<KanbanBoard>({
    queryKey: ["tasks", "board"],
    queryFn: async () => (await api.get("/tasks/board")).data,
  });
}

function isOverdue(task: Task) {
  if (!task.due_date) return false;
  if (task.status === "filed" || task.status === "completed") return false;
  return new Date(task.due_date) < new Date();
}

function TaskCard({ task, onDragStart }: { task: Task; onDragStart: (id: string) => void }) {
  const overdue = isOverdue(task);
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart(task.id);
      }}
      className="cursor-grab select-none rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg-elevated)] p-3 text-sm shadow-sm active:cursor-grabbing"
    >
      <p className="font-medium text-[var(--ink)]">{task.title}</p>
      {task.description && (
        <p className="mt-1 line-clamp-2 text-xs text-[var(--ink-muted)]">
          {task.description}
        </p>
      )}
      {task.due_date && (
        <div className="mt-2">
          <Badge tone={overdue ? "overdue" : "neutral"}>
            <Clock size={11} />
            <span className="tabular">
              {new Date(task.due_date).toLocaleDateString("en-IN")}
            </span>
          </Badge>
        </div>
      )}
    </div>
  );
}

export default function WorkflowBoardPage() {
  const { data, isLoading, isError, error } = useBoard();
  const queryClient = useQueryClient();
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<TaskStatus | null>(null);

  if (isError) throw error;

  const { mutate: moveTask } = useMutation({
    mutationFn: async ({ taskId, status }: { taskId: string; status: TaskStatus }) =>
      (await api.patch(`/tasks/${taskId}/status`, { status })).data,
    onMutate: async ({ taskId, status }) => {
      await queryClient.cancelQueries({ queryKey: ["tasks", "board"] });
      const previous = queryClient.getQueryData<KanbanBoard>(["tasks", "board"]);

      if (previous) {
        const next: KanbanBoard = { columns: { ...previous.columns } };
        let moved: Task | undefined;
        for (const key of Object.keys(next.columns) as TaskStatus[]) {
          const idx = next.columns[key].findIndex((t) => t.id === taskId);
          if (idx !== -1) {
            moved = next.columns[key][idx];
            next.columns[key] = next.columns[key].filter((t) => t.id !== taskId);
            break;
          }
        }
        if (moved) {
          next.columns[status] = [...next.columns[status], { ...moved, status }];
        }
        queryClient.setQueryData(["tasks", "board"], next);
      }

      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["tasks", "board"], context.previous);
      }
      toast.error("Couldn't move that task. Please try again.");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks", "board"] });
    },
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/3" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-72 w-full" />
          ))}
        </div>
      </div>
    );
  }

  const isEmpty = Object.values(data.columns).every((tasks) => tasks.length === 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
          Workflow board
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Drag a card into the next stage to move it forward.
        </p>
      </div>

      {isEmpty ? (
        <EmptyState
          icon={LayoutGrid}
          title="No tasks yet"
          description="Tasks created for a client or filing will appear here, grouped by stage."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
          {KANBAN_COLUMNS.map((column) => {
            const tasks = data.columns[column.key] ?? [];
            return (
              <div
                key={column.key}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOverColumn(column.key);
                }}
                onDragLeave={() => setDragOverColumn((c) => (c === column.key ? null : c))}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOverColumn(null);
                  if (draggingId) {
                    moveTask({ taskId: draggingId, status: column.key });
                    setDraggingId(null);
                  }
                }}
              >
                <Card
                  className={cn(
                    "flex h-full min-h-[16rem] flex-col gap-3 p-3 transition-colors",
                    dragOverColumn === column.key && "border-[var(--brass)]/50 bg-[var(--brass)]/[0.05]"
                  )}
                >
                  <div className="flex items-center justify-between px-1">
                    <h2 className="text-xs font-medium uppercase tracking-wide text-[var(--ink-muted)]">
                      {column.label}
                    </h2>
                    <span className="tabular text-xs text-[var(--ink-faint)]">
                      {tasks.length}
                    </span>
                  </div>
                  <div className="flex flex-1 flex-col gap-2">
                    {tasks.map((task) => (
                      <TaskCard key={task.id} task={task} onDragStart={setDraggingId} />
                    ))}
                  </div>
                </Card>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
