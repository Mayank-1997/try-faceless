'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@ai-video-studio/platform-kernel'
import { getSDK } from '@ai-video-studio/platform-sdk'
import { Button, Input, Card, CardContent, CardHeader, CardTitle, CardDescription } from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import { Video, Mail, Lock, User, Loader2 } from '@ai-video-studio/icons'

export default function RegisterPage() {
  const router = useRouter()
  const { addToast } = useToast()
  const setUser = useAuthStore((s) => s.setUser)
  const setTokens = useAuthStore((s) => s.setTokens)

  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    first_name: '',
    last_name: '',
  })
  const [loading, setLoading] = useState(false)

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await getSDK().auth.register(form)
      const res = await getSDK().auth.login({ email: form.email, password: form.password })
      setUser(res.user)
      setTokens(res.access_token, res.refresh_token)
      addToast({ title: 'Account created!', variant: 'success' })
      router.push('/dashboard')
    } catch (err) {
      addToast({
        title: 'Registration failed',
        description: err instanceof Error ? err.message : 'Something went wrong',
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)] p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex items-center gap-2">
            <Video className="h-8 w-8 text-[var(--brand-default)]" />
            <span className="text-xl font-bold">AI Video Studio</span>
          </div>
          <CardTitle>Create Account</CardTitle>
          <CardDescription>Sign up to start creating AI-powered videos</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-sm font-medium">First Name</label>
                <Input
                  value={form.first_name}
                  onChange={(e) => update('first_name', e.target.value)}
                  placeholder="John"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Last Name</label>
                <Input
                  value={form.last_name}
                  onChange={(e) => update('last_name', e.target.value)}
                  placeholder="Doe"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fg-muted)]" />
                <Input
                  value={form.username}
                  onChange={(e) => update('username', e.target.value)}
                  placeholder="johndoe"
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fg-muted)]" />
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => update('email', e.target.value)}
                  placeholder="you@example.com"
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fg-muted)]" />
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => update('password', e.target.value)}
                  placeholder="••••••••"
                  className="pl-9"
                  required
                  minLength={8}
                />
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-[var(--fg-muted)]">
            Already have an account?{' '}
            <Link href="/login" className="font-medium text-[var(--brand-default)] hover:underline">
              Sign In
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
