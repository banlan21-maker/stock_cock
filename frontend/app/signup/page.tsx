
import AuthForm from '@/components/auth/AuthForm'

export default function SignUpPage() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center py-2">
            <AuthForm view="signup" />
        </div>
    )
}
