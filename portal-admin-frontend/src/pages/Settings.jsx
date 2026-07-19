import React, { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import { Save, ShieldCheck } from 'lucide-react';

export default function Settings() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    webhook_target_url: '',
    shared_secret: '',
    is_active: true
  });

  useEffect(() => {
    const loadSettings = async () => {
      try {
        setLoading(true);
        const res = await getSettings();
        setSettings({
          webhook_target_url: res.webhook_target_url || '',
          shared_secret: res.shared_secret || '',
          is_active: res.is_active
        });
      } catch (err) {
        addToast(err.message, "error");
      } finally {
        setLoading(false);
      }
    };
    loadSettings();
  }, [addToast]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      const res = await updateSettings({
        webhook_target_url: settings.webhook_target_url,
        shared_secret: settings.shared_secret,
        is_active: settings.is_active
      });
      setSettings(res);
      addToast("Settings saved successfully");
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8 max-w-3xl animate-fade-in-up">
        <Skeleton className="h-10 w-48 mb-2" />
        <Card>
          <CardHeader className="bg-muted/20 border-b">
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-6 w-32" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-3xl animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure Webhook Destinations and System Parameters</p>
      </div>

      <Card>
        <CardHeader className="border-b py-4 bg-muted/20 flex flex-row items-center gap-3">
          <ShieldCheck className="w-5 h-5 text-muted-foreground" />
          <CardTitle className="text-lg">Webhook Configuration</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="p-6 space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Target URL</label>
              <p className="text-xs text-muted-foreground mb-2">The endpoint where webhook events will be delivered via POST.</p>
              <Input
                type="url"
                value={settings.webhook_target_url}
                onChange={(e) => setSettings({ ...settings, webhook_target_url: e.target.value })}
                placeholder="https://example.com/api/webhooks"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Shared Secret</label>
              <p className="text-xs text-muted-foreground mb-2">Used to sign webhook payloads (X-Signature header).</p>
              <Input
                type="password"
                value={settings.shared_secret}
                onChange={(e) => setSettings({ ...settings, shared_secret: e.target.value })}
                className="font-mono"
                placeholder="Super secret key"
                required
              />
            </div>

            <div className="flex items-center space-x-2 pt-2">
              <input
                id="is_active"
                type="checkbox"
                checked={settings.is_active}
                onChange={(e) => setSettings({ ...settings, is_active: e.target.checked })}
                className="h-4 w-4 rounded border-input text-primary focus:ring-primary bg-background"
              />
              <label htmlFor="is_active" className="text-sm font-medium text-foreground leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                Enable Webhook Delivery
              </label>
            </div>
          </CardContent>
          <CardFooter className="px-6 py-4 border-t bg-muted/20">
            <Button
              type="submit"
              disabled={saving}
              isLoading={saving}
              className="gap-2"
            >
              <Save className="w-4 h-4" />
              Save Settings
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
