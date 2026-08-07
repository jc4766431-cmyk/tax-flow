"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-auth";
import { useClientsList } from "@/hooks/use-clients";
import { Modal } from "@/components/dashboard/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { StaffMember, Task } from "@/lib/types";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function useStaffForAssignment(firmId: string | undefined) {
  return useQuery<StaffMember[]>({
    queryKey: ["users", firmId],
    queryFn: async () => (await api.get("/users", { params: { firm_id: firmId } })).data,
    enabled: !!firmId,
  });
}

function toDateInputValue(iso: string | null) {
  if (!iso) return "";
  return iso.slice(0, 10);
}

// Handles both create (task=null) and edit (task set) — mirrors the doc's
// call for full-field edit via PATCH /tasks/{id}, kept separate from the
// board's drag-and-drop PATCH /tasks/{id}/status mutation.
export function TaskModal({
  open,
  onClose,
  task,
}: {
  open: boolean;
  onClose: () => void;
  task: Task | null;
}) {
  const { data: currentUser } = useCurrentUser();
  const queryClient = useQueryClient();
  const { data: staff } = useStaffForAssignment(currentUser?.firm_id ?? undefined);
  const { data: clientsPage } = useClientsList();
  const clients = clientsPage?.items ?? [];
  const isEdit = !!task;

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [clientId, setClientId] = useState("");
  const [assignedToId, setAssignedToId] = useState("");
  const [dueDate, setDueDate] = useState("");

  useEffect(() => {
    if (open) {
      setTitle(task?.title ?? "");
      setDescription(task?.description ?? "");
      setClientId(task?.client_id ?? "");
      setAssignedToId(task?.assigned_to_id ?? "");
      setDueDate(toDateInputValue(task?.due_date ?? null));
    }
  }, [open, task]);

  function invalidateBoard() {
    queryClient.invalidateQueries({ queryKey: ["tasks", "board"] });
  }

  const save = useMutation({
    mutationFn: async () => {
      const body = {
        title,
        description: description || null,
        client_id: clientId || null,
        assigned_to_id: assignedToId || null,
        due_date: dueDate || null,
      };
      if (isEdit) {
        return (await api.patch(`/tasks/${task!.id}`, body)).data;
      }
      return (await api.post("/tasks", body)).data;
    },
    onSuccess: () => {
      toast.success(isEdit ? "Task updated" : "Task created");
      invalidateBoard();
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't save that task.")),
  });

  const remove = useMutation({
    mutationFn: async () => api.delete(`/tasks/${task!.id}`),
    onSuccess: () => {
      toast.success("Task deleted");
      invalidateBoard();
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't delete that task.")),
  });

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? "Edit task" : "New task"}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (title.trim()) save.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="task-title">Title</Label>
          <Input
            id="task-title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Collect Q1 GST invoices"
          />
        </div>
        <div>
          <Label htmlFor="task-description">Description</Label>
          <Textarea
            id="task-description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="task-client">Client (optional)</Label>
          <Select id="task-client" value={clientId} onChange={(e) => setClientId(e.target.value)}>
            <option value="">No client</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.company_name ?? c.id.slice(0, 8)}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="task-assignee">Assigned to (optional)</Label>
          <Select
            id="task-assignee"
            value={assignedToId}
            onChange={(e) => setAssignedToId(e.target.value)}
          >
            <option value="">Unassigned</option>
            {(staff ?? [])
              .filter((s) => s.role !== "client")
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name} ({s.role.replace("_", " ")})
                </option>
              ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="task-due-date">Due date</Label>
          <Input
            id="task-due-date"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 pt-1">
          <Button type="submit" disabled={save.isPending || !title.trim()} className="flex-1">
            {save.isPending ? "Saving…" : isEdit ? "Save changes" : "Create task"}
          </Button>
          {isEdit && (
            <Button
              type="button"
              variant="outline"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
              title="Delete task"
            >
              <Trash2 size={16} />
            </Button>
          )}
        </div>
      </form>
    </Modal>
  );
}
