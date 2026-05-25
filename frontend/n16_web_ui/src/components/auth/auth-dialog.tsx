"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function AuthDialog({ open, onOpenChange }: Props) {
  const { login } = useAuth();
  const [tab, setTab] = useState<string>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  function reset() {
    setUsername("");
    setPassword("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      toast.error("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu");
      return;
    }

    setLoading(true);
    try {
      const payload = { username: username.trim(), password };

      if (tab === "register") {
        const res = await apiClient.auth.register(payload);
        if (res.status === "error") {
          toast.error(res.message);
          return;
        }
        toast.success("Đăng ký thành công! Đang đăng nhập...");
        const loginRes = await apiClient.auth.login(payload);
        if (loginRes.status === "success" && loginRes.user_id) {
          login(loginRes.user_id, username.trim(), loginRes.token);
          reset();
          onOpenChange(false);
        }
      } else {
        const res = await apiClient.auth.login(payload);
        if (res.status === "error") {
          toast.error(res.message);
          return;
        }
        if (res.user_id) {
          login(res.user_id, username.trim(), res.token);
          toast.success(`Xin chào, ${username.trim()}!`);
          reset();
          onOpenChange(false);
        }
      }
    } catch {
      toast.error("Không thể kết nối đến máy chủ");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xs">
        <DialogHeader>
          <DialogTitle>Tài khoản</DialogTitle>
        </DialogHeader>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full">
            <TabsTrigger value="login" className="flex-1">
              Đăng nhập
            </TabsTrigger>
            <TabsTrigger value="register" className="flex-1">
              Đăng ký
            </TabsTrigger>
          </TabsList>

          <TabsContent value={tab}>
            <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="username">Tên đăng nhập</Label>
                <Input
                  id="username"
                  placeholder="Nhập tên đăng nhập"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="password">Mật khẩu</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Nhập mật khẩu"
                  autoComplete={tab === "register" ? "new-password" : "current-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
              <Button type="submit" className="mt-1 w-full" disabled={loading}>
                {loading && <Loader2 className="size-4 animate-spin" />}
                {tab === "register" ? "Tạo tài khoản" : "Đăng nhập"}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
