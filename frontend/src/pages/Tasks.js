import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Plus, Clock, CheckCircle2, PlayCircle, XCircle, ClipboardList, Building2, Calendar, User, AlertTriangle } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const TASK_TYPES = [
  { value: "cleaning", label: "Cleaning", color: "bg-blue-500/10 text-blue-600" },
  { value: "maintenance", label: "Maintenance", color: "bg-amber-500/10 text-amber-600" },
  { value: "check_in", label: "Check-in", color: "bg-emerald-500/10 text-emerald-600" },
  { value: "check_out", label: "Check-out", color: "bg-purple-500/10 text-purple-600" },
  { value: "admin", label: "Admin", color: "bg-slate-500/10 text-slate-600" },
  { value: "general", label: "General", color: "bg-primary/10 text-primary" },
];

const PRIORITIES = [
  { value: "low", label: "Low", color: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  { value: "medium", label: "Medium", color: "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400" },
  { value: "high", label: "High", color: "bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400" },
  { value: "urgent", label: "Urgent", color: "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400" },
];

const STATUS_CONFIG = {
  pending: { label: "Pending", icon: Clock, color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10" },
  in_progress: { label: "In Progress", icon: PlayCircle, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10" },
  completed: { label: "Completed", icon: CheckCircle2, color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10" },
  cancelled: { label: "Cancelled", icon: XCircle, color: "text-slate-600 dark:text-slate-400", bg: "bg-slate-500/10" },
};

const empty = {
  title: "",
  description: "",
  task_type: "general",
  property_id: "",
  assigned_staff_id: "",
  due_date: "",
  priority: "medium",
};

function TaskCard({ task, isAdmin, onEdit, onStatusChange, index = 0 }) {
  const typeConfig = TASK_TYPES.find(t => t.value === task.task_type) || TASK_TYPES[5];
  const priorityConfig = PRIORITIES.find(p => p.value === task.priority) || PRIORITIES[1];
  const statusConfig = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;

  return (
    <Card 
      className="group hover:shadow-lg hover:-translate-y-1 transition-all duration-200 animate-fade-in opacity-0" 
      data-testid={`task-card-${task.id}`}
      style={{ animationDelay: `${0.05 + index * 0.03}s` }}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <div className={`h-8 w-8 rounded-lg ${statusConfig.bg} flex items-center justify-center shrink-0 transition-transform group-hover:scale-110`}>
              <StatusIcon className={`h-4 w-4 ${statusConfig.color}`} />
            </div>
            <div className="min-w-0">
              <h3 className="font-medium text-sm truncate text-foreground">{task.title}</h3>
              <Badge className={`text-xs ${typeConfig.color} border-0`}>{typeConfig.label}</Badge>
            </div>
          </div>
          <Badge className={`shrink-0 ${priorityConfig.color} border-0`}>
            {priorityConfig.label}
          </Badge>
        </div>

        {task.description && (
          <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{task.description}</p>
        )}

        <div className="space-y-2 text-sm text-muted-foreground mb-4">
          {task.property_name && (
            <div className="flex items-center gap-2">
              <Building2 className="h-3.5 w-3.5 shrink-0 text-primary/60" />
              <span className="truncate">{task.property_name}</span>
            </div>
          )}
          {task.assigned_staff_name && (
            <div className="flex items-center gap-2">
              <User className="h-3.5 w-3.5 shrink-0 text-primary/60" />
              <span>{task.assigned_staff_name}</span>
            </div>
          )}
          {task.due_date && (
            <div className="flex items-center gap-2">
              <Calendar className="h-3.5 w-3.5 shrink-0 text-primary/60" />
              <span>Due: {task.due_date}</span>
            </div>
          )}
        </div>

        {/* Status Actions */}
        <div className="flex gap-2 pt-3 border-t">
          {task.status === "pending" && (
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-1 hover:bg-primary/5 hover:border-primary/30 hover:text-primary"
              onClick={() => onStatusChange(task.id, "in_progress")}
              data-testid={`start-task-${task.id}`}
            >
              <PlayCircle className="h-3.5 w-3.5 mr-1.5" />Start
            </Button>
          )}
          {task.status === "in_progress" && (
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-1 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 hover:border-emerald-300"
              onClick={() => onStatusChange(task.id, "completed")}
              data-testid={`complete-task-${task.id}`}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />Complete
            </Button>
          )}
          {isAdmin && task.status !== "completed" && task.status !== "cancelled" && (
            <Button 
              variant="ghost" 
              size="sm"
              className="hover:bg-primary/10 hover:text-primary"
              onClick={() => onEdit(task)}
              data-testid={`edit-task-${task.id}`}
            >
              Edit
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function Tasks() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [staff, setStaff] = useState([]);
  const [properties, setProperties] = useState([]);
  const [summary, setSummary] = useState({ pending: 0, in_progress: 0, completed_this_month: 0 });
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("pending");

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [taskRes, summaryRes, staffRes, propRes] = await Promise.all([
        fetch(`${API}/api/tasks`, { credentials: "include" }),
        fetch(`${API}/api/tasks/my-summary`, { credentials: "include" }),
        fetch(`${API}/api/staff`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
      ]);
      if (taskRes.ok) setTasks(await taskRes.json());
      if (summaryRes.ok) setSummary(await summaryRes.json());
      if (staffRes.ok) setStaff(await staffRes.json());
      if (propRes.ok) setProperties(await propRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]); // eslint-disable-line

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error("Task title is required"); return; }
    if (!form.assigned_staff_id) { toast.error("Please assign a staff member"); return; }
    
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/tasks/${editing}` : `${API}/api/tasks`;
      const res = await fetch(url, { 
        method, 
        headers: { "Content-Type": "application/json" }, 
        credentials: "include", 
        body: JSON.stringify(form) 
      });
      if (res.ok) {
        toast.success(editing ? "Task updated" : "Task created");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { 
        const err = await res.json(); 
        toast.error(err.detail || "Failed"); 
      }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      const res = await fetch(`${API}/api/tasks/${taskId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        toast.success(`Task ${newStatus === "completed" ? "completed" : "started"}!`);
        fetchData();
      }
    } catch (err) { toast.error("Failed to update task"); }
  };

  const openEdit = (task) => {
    setForm({
      title: task.title,
      description: task.description || "",
      task_type: task.task_type,
      property_id: task.property_id || "",
      assigned_staff_id: task.assigned_staff_id,
      due_date: task.due_date || "",
      priority: task.priority,
    });
    setEditing(task.id); 
    setDialogOpen(true);
  };

  if (authLoading || !user) {
    return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  const isAdmin = user?.role === "company_admin";
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const filteredTasks = tasks.filter(t => {
    if (activeTab === "all") return true;
    return t.status === activeTab;
  });

  const taskCounts = {
    all: tasks.length,
    pending: tasks.filter(t => t.status === "pending").length,
    in_progress: tasks.filter(t => t.status === "in_progress").length,
    completed: tasks.filter(t => t.status === "completed").length,
  };

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="tasks-page">
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Tasks</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {isAdmin ? `${tasks.length} total tasks` : `Your assigned tasks`}
            </p>
          </div>
          {isAdmin && (
            <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-task-btn" className="shadow-sm">
              <Plus className="mr-2 h-4 w-4" />Add Task
            </Button>
          )}
        </div>

        {/* Summary Cards for Staff */}
        {!isAdmin && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-5 flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-amber-500/10 flex items-center justify-center">
                  <Clock className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{summary.pending}</p>
                  <p className="text-sm text-muted-foreground">Pending</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <PlayCircle className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{summary.in_progress}</p>
                  <p className="text-sm text-muted-foreground">In Progress</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                  <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{summary.completed_this_month}</p>
                  <p className="text-sm text-muted-foreground">Completed (MTD)</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1,2,3].map(i => <Card key={i}><CardContent className="p-6 h-40 animate-pulse bg-muted" /></Card>)}
          </div>
        ) : tasks.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="p-12 text-center">
              <ClipboardList className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No tasks yet</p>
              {isAdmin && (
                <Button className="mt-4" onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }}>
                  <Plus className="mr-2 h-4 w-4" />Create First Task
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList data-testid="task-tabs">
                <TabsTrigger value="pending" className="gap-2">
                  <Clock className="h-4 w-4" />Pending
                  <Badge variant="secondary">{taskCounts.pending}</Badge>
                </TabsTrigger>
                <TabsTrigger value="in_progress" className="gap-2">
                  <PlayCircle className="h-4 w-4" />In Progress
                  <Badge variant="secondary">{taskCounts.in_progress}</Badge>
                </TabsTrigger>
                <TabsTrigger value="completed" className="gap-2">
                  <CheckCircle2 className="h-4 w-4" />Completed
                  <Badge variant="secondary">{taskCounts.completed}</Badge>
                </TabsTrigger>
                <TabsTrigger value="all" className="gap-2">
                  All
                  <Badge variant="secondary">{taskCounts.all}</Badge>
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredTasks.map((task, index) => (
                <TaskCard 
                  key={task.id}
                  task={task}
                  isAdmin={isAdmin}
                  onEdit={openEdit}
                  onStatusChange={handleStatusChange}
                  index={index}
                />
              ))}
            </div>

            {filteredTasks.length === 0 && (
              <Card className="border-dashed">
                <CardContent className="p-8 text-center text-muted-foreground">
                  No {activeTab === "all" ? "" : activeTab.replace("_", " ")} tasks
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading">{editing ? "Edit Task" : "Create Task"}</DialogTitle>
              <DialogDescription>Assign tasks to staff members for properties.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2">
                <Label>Task Title *</Label>
                <Input 
                  value={form.title} 
                  onChange={e => set("title", e.target.value)} 
                  placeholder="e.g., Clean apartment after checkout"
                  data-testid="task-title-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea 
                  value={form.description} 
                  onChange={e => set("description", e.target.value)} 
                  placeholder="Additional details..."
                  rows={2}
                  data-testid="task-description-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Task Type</Label>
                  <Select value={form.task_type} onValueChange={v => set("task_type", v)}>
                    <SelectTrigger data-testid="task-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TASK_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Priority</Label>
                  <Select value={form.priority} onValueChange={v => set("priority", v)}>
                    <SelectTrigger data-testid="task-priority-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {PRIORITIES.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Assign to Staff *</Label>
                <Select value={form.assigned_staff_id} onValueChange={v => set("assigned_staff_id", v)}>
                  <SelectTrigger data-testid="task-staff-select"><SelectValue placeholder="Select staff..." /></SelectTrigger>
                  <SelectContent>
                    {staff.filter(s => s.active).map(s => (
                      <SelectItem key={s.id} value={s.id}>{s.first_name} {s.last_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Property (Optional)</Label>
                <Select value={form.property_id || "none"} onValueChange={v => set("property_id", v === "none" ? "" : v)}>
                  <SelectTrigger data-testid="task-property-select"><SelectValue placeholder="Select property..." /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Property</SelectItem>
                    {properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Due Date</Label>
                <Input 
                  type="date"
                  value={form.due_date} 
                  onChange={e => set("due_date", e.target.value)}
                  data-testid="task-duedate-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={saving} data-testid="save-task-btn">
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
