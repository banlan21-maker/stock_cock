import Link from 'next/link'
import { createClient } from '@/utils/supabase/server'
import LogoutButton from '@/components/auth/LogoutButton'
import { User, Rocket } from 'lucide-react'

export default async function Header() {
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()

    return (
        <header className="w-full border-b border-white/10 bg-navy/50 backdrop-blur-md sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2 font-bold text-xl">
                    <Rocket className="w-6 h-6 text-blue-500" />
                    <span>Stock Cock</span>
                </Link>

                <div className="flex items-center gap-4">
                    {user ? (
                        <div className="flex items-center gap-4">
                            <span className="text-sm text-gray-400">
                                {user.email}
                            </span>
                            <LogoutButton />
                        </div>
                    ) : (
                        <div className="flex items-center gap-4">
                            <Link
                                href="/login"
                                className="text-sm text-gray-300 hover:text-white transition-colors"
                            >
                                로그인
                            </Link>
                            <Link
                                href="/signup"
                                className="text-sm px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                            >
                                회원가입
                            </Link>
                        </div>
                    )}
                </div>
            </div>
        </header>
    )
}
