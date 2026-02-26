'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/utils/supabase/client'
import { Loader2 } from 'lucide-react'

function GoogleIcon({ className }: { className?: string }) {
    return (
        <svg className={className} viewBox="0 0 24 24" aria-hidden>
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
        </svg>
    )
}

function KakaoIcon({ className }: { className?: string }) {
    return (
        <svg className={className} viewBox="0 0 24 24" fill="#191919" aria-hidden>
            <path d="M12 3c-5.8 0-10.5 3.66-10.5 8.18 0 2.85 1.89 5.37 4.72 6.84-.2.73-.73 2.66-.84 3.09-.14.53.2.52.41.38.18-.11 2.83-1.92 3.9-2.64.54.08 1.11.12 1.71.12 5.8 0 10.5-3.66 10.5-8.18S17.8 3 12 3z" />
        </svg>
    )
}

interface AuthFormProps {
    view: 'login' | 'signup'
}

export default function AuthForm({ view }: AuthFormProps) {
    const router = useRouter()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [message, setMessage] = useState<string | null>(null)
    const [socialLoading, setSocialLoading] = useState<'google' | 'kakao' | null>(null)

    const supabase = createClient()

    const handleOAuth = async (provider: 'google' | 'kakao') => {
        setSocialLoading(provider)
        setError(null)
        const { error } = await supabase.auth.signInWithOAuth({
            provider,
            options: {
                redirectTo: `${location.origin}/auth/callback`,
            },
        })
        if (error) {
            setError(error.message)
            setSocialLoading(null)
        }
        // 성공 시 Supabase가 OAuth 페이지로 리다이렉트하므로 여기서는 아무것도 안 함
    }

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setError(null)
        setMessage(null)

        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        })

        if (error) {
            setError(error.message)
            setLoading(false)
        } else {
            router.push('/')
            router.refresh()
        }
    }

    const handleSignUp = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setError(null)
        setMessage(null)

        const { error } = await supabase.auth.signUp({
            email,
            password,
            options: {
                emailRedirectTo: `${location.origin}/auth/callback`,
            },
        })

        if (error) {
            if (error.message.includes('security purposes') || error.message.includes('rate limit')) {
                setError('보안 또는 호출 제한으로 인해 잠시 후 다시 시도해주세요. (대기 필요)')
            } else {
                setError(error.message)
            }
            setLoading(false)
        } else {
            // Check if email confirmation is required (Supabase default)
            // Usually sign up returns a session if strict confirmation is off, or no session if on.
            setMessage('회원가입 확인 메일을 발송했습니다. 이메일을 확인해주세요.')
            setLoading(false)
        }
    }

    return (
        <div className="w-full max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">
                {view === 'login' ? '로그인' : '회원가입'}
            </h2>

            <form onSubmit={view === 'login' ? handleLogin : handleSignUp} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
                        이메일
                    </label>
                    <input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="example@email.com"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
                        비밀번호
                    </label>
                    <input
                        id="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="••••••••"
                    />
                </div>

                {error && (
                    <div className="p-3 text-sm text-red-500 bg-red-50 rounded-md">
                        {error}
                    </div>
                )}

                {message && (
                    <div className="p-3 text-sm text-blue-600 bg-blue-50 rounded-md">
                        {message}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center"
                >
                    {loading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        view === 'login' ? '로그인' : '가입하기'
                    )}
                </button>
            </form>

            {/* 로그인·회원가입 공통: 소셜 로그인 (회원가입에서도 소셜로 바로 가입 가능) */}
            <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-white text-gray-500">소셜 로그인</span>
                </div>
            </div>
            <div className="space-y-2">
                <button
                    type="button"
                    onClick={() => handleOAuth('google')}
                    disabled={!!socialLoading}
                    className="w-full py-2.5 px-4 bg-white border border-gray-300 rounded-md font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    {socialLoading === 'google' ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        <>
                            <GoogleIcon className="w-5 h-5" />
                            Google로 로그인
                        </>
                    )}
                </button>
                <button
                    type="button"
                    onClick={() => handleOAuth('kakao')}
                    disabled={!!socialLoading}
                    className="w-full py-2.5 px-4 bg-[#FEE500] border border-[#FEE500] rounded-md font-medium text-[#191919] hover:bg-[#FDD835] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    {socialLoading === 'kakao' ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        <>
                            <KakaoIcon className="w-5 h-5" />
                            카카오로 로그인
                        </>
                    )}
                </button>
            </div>

            <div className="mt-4 text-center text-sm text-gray-600">
                {view === 'login' ? (
                    <p>
                        계정이 없으신가요?{' '}
                        <Link href="/signup" className="text-blue-600 hover:underline">
                            회원가입
                        </Link>
                    </p>
                ) : (
                    <p>
                        이미 계정이 있으신가요?{' '}
                        <Link href="/login" className="text-blue-600 hover:underline">
                            로그인
                        </Link>
                    </p>
                )}
            </div>
        </div>
    )
}
