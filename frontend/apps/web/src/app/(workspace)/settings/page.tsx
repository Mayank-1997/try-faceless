'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useAuthStore, useTheme } from '@ai-video-studio/platform-kernel'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, Button, Select, Badge, Input, Label } from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  User, Palette, Bell, Shield, ArrowLeft,
  Cpu, Mic, HardDrive, Image, Brush,
  Check, Key,
} from '@ai-video-studio/icons'

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user)
  const { theme, setTheme } = useTheme()
  const { addToast } = useToast()

  const [brandColor, setBrandColor] = useState('#6366f1')
  const [fontFamily, setFontFamily] = useState('Inter')
  const [watermarkUrl, setWatermarkUrl] = useState('')
  const [geminiModel, setGeminiModel] = useState('gemini-2.0-flash')
  const [veoModel, setVeoModel] = useState('veo-3.0')
  const [imagenModel, setImagenModel] = useState('imagen-3.0')
  const [ttsModel, setTtsModel] = useState('google-tts')
  const [voiceProvider, setVoiceProvider] = useState('google')
  const [voiceId, setVoiceId] = useState('en-US-Standard-A')
  const [voiceSpeed, setVoiceSpeed] = useState('1.0')

  const handleSave = (section: string) => {
    addToast({ title: `${section} settings saved`, variant: 'success' })
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link href="/dashboard">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-[var(--fg-default)]">Settings</h1>
          <p className="text-sm text-[var(--fg-muted)]">Manage your account and preferences</p>
        </div>
      </div>

      {/* Profile */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Profile</CardTitle>
          </div>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {user && (
            <>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Name</span>
                <span className="font-medium text-[var(--fg-default)]">{user.full_name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Email</span>
                <span className="font-medium text-[var(--fg-default)]">{user.email}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Username</span>
                <span className="font-medium text-[var(--fg-default)]">{user.username}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Status</span>
                <Badge variant={user.status === 'active' ? 'success' : 'warning'}>{user.status}</Badge>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Appearance</CardTitle>
          </div>
          <CardDescription>Customize how the app looks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-[var(--fg-muted)]">Theme</span>
            <Select
              value={theme}
              onChange={(e) => {
                setTheme(e.target.value as 'light' | 'dark' | 'system')
                addToast({ title: 'Theme updated', variant: 'success' })
              }}
              className="w-32"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Brand Kit */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Brush className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Brand Kit</CardTitle>
          </div>
          <CardDescription>Customize branding for your videos</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="brand-color">Primary Color</Label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  id="brand-color"
                  value={brandColor}
                  onChange={(e) => setBrandColor(e.target.value)}
                  className="h-9 w-12 cursor-pointer rounded border border-[var(--border-default)]"
                />
                <Input value={brandColor} onChange={(e) => setBrandColor(e.target.value)} className="flex-1" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="font-family">Font Family</Label>
              <Select id="font-family" value={fontFamily} onChange={(e) => setFontFamily(e.target.value)}>
                <option value="Inter">Inter</option>
                <option value="Roboto">Roboto</option>
                <option value="Poppins">Poppins</option>
                <option value="Montserrat">Montserrat</option>
              </Select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="watermark">Watermark URL</Label>
              <Input
                id="watermark"
                value={watermarkUrl}
                onChange={(e) => setWatermarkUrl(e.target.value)}
                placeholder="https://example.com/logo.png"
              />
            </div>
          </div>
          <Button size="sm" onClick={() => handleSave('Brand kit')}>Save Brand Kit</Button>
        </CardContent>
      </Card>

      {/* AI Providers */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>AI Providers</CardTitle>
          </div>
          <CardDescription>Configure AI model preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ProviderRow name="Gemini (LLM)" icon={Cpu} model={geminiModel} onModelChange={setGeminiModel} options={['gemini-2.0-flash', 'gemini-2.0-pro', 'gemini-1.5-flash']} configured />
          <ProviderRow name="VEO (Video)" icon={Image} model={veoModel} onModelChange={setVeoModel} options={['veo-3.0', 'veo-2.0']} configured />
          <ProviderRow name="Imagen (Images)" icon={Image} model={imagenModel} onModelChange={setImagenModel} options={['imagen-3.0', 'imagen-2.0']} configured />
          <ProviderRow name="TTS (Voice)" icon={Mic} model={ttsModel} onModelChange={setTtsModel} options={['google-tts', 'elevenlabs']} configured />
          <Button size="sm" onClick={() => handleSave('AI providers')}>Save Provider Settings</Button>
        </CardContent>
      </Card>

      {/* Voices */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Mic className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Voices</CardTitle>
          </div>
          <CardDescription>Default voice settings for narration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="voice-provider">Provider</Label>
              <Select id="voice-provider" value={voiceProvider} onChange={(e) => setVoiceProvider(e.target.value)}>
                <option value="google">Google TTS</option>
                <option value="elevenlabs">ElevenLabs</option>
                <option value="azure">Azure</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="voice-id">Voice ID</Label>
              <Input id="voice-id" value={voiceId} onChange={(e) => setVoiceId(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="voice-speed">Speed</Label>
              <Select id="voice-speed" value={voiceSpeed} onChange={(e) => setVoiceSpeed(e.target.value)}>
                <option value="0.75">0.75x</option>
                <option value="1.0">1.0x (Normal)</option>
                <option value="1.25">1.25x</option>
                <option value="1.5">1.5x</option>
              </Select>
            </div>
          </div>
          <Button size="sm" onClick={() => handleSave('Voice')}>Save Voice Settings</Button>
        </CardContent>
      </Card>

      {/* Storage */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <HardDrive className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Storage</CardTitle>
          </div>
          <CardDescription>Manage your storage usage</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--fg-muted)]">Used</span>
              <span className="font-medium text-[var(--fg-default)]">2.3 GB / 5 GB</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-subtle)]">
              <div className="h-full rounded-full bg-[var(--brand-default)]" style={{ width: '46%' }} />
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--fg-muted)]">46% used</span>
              <Button variant="outline" size="sm">Manage Files</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Notifications</CardTitle>
          </div>
          <CardDescription>Manage notification preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { label: 'Project completed', email: true, inApp: true },
            { label: 'Render finished', email: false, inApp: true },
            { label: 'Publishing done', email: true, inApp: true },
            { label: 'Billing alerts', email: true, inApp: false },
          ].map((item) => (
            <div key={item.label} className="flex items-center justify-between text-sm">
              <span className="text-[var(--fg-default)]">{item.label}</span>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1 text-xs text-[var(--fg-muted)]">
                  <input type="checkbox" defaultChecked={item.email} className="accent-[var(--brand-default)]" />
                  Email
                </label>
                <label className="flex items-center gap-1 text-xs text-[var(--fg-muted)]">
                  <input type="checkbox" defaultChecked={item.inApp} className="accent-[var(--brand-default)]" />
                  In-app
                </label>
              </div>
            </div>
          ))}
          <Button size="sm" onClick={() => handleSave('Notification')}>Save Preferences</Button>
        </CardContent>
      </Card>

      {/* Security */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Security</CardTitle>
          </div>
          <CardDescription>Account security settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {user && (
            <div className="flex justify-between text-sm">
              <span className="text-[var(--fg-muted)]">2FA</span>
              <Badge variant={user.two_factor_enabled ? 'success' : 'outline'}>
                {user.two_factor_enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-[var(--fg-muted)]" />
            <Button variant="outline" size="sm">Change Password</Button>
          </div>
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href="/billing">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to billing
          </Button>
        </Link>
        <Link href="/admin">
          <Button variant="outline">Go to admin</Button>
        </Link>
      </div>
    </div>
  )
}

function ProviderRow({
  name,
  icon: Icon,
  model,
  onModelChange,
  options,
  configured,
}: {
  name: string
  icon: React.ComponentType<{ className?: string }>
  model: string
  onModelChange: (v: string) => void
  options: string[]
  configured: boolean
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] p-3">
      <Icon className="h-5 w-5 shrink-0 text-[var(--fg-muted)]" />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--fg-default)]">{name}</span>
          {configured ? (
            <Badge variant="success">
              <Check className="mr-1 h-3 w-3" />
              Connected
            </Badge>
          ) : (
            <Badge variant="warning">Not configured</Badge>
          )}
        </div>
      </div>
      <Select value={model} onChange={(e) => onModelChange(e.target.value)} className="w-40">
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </Select>
    </div>
  )
}
