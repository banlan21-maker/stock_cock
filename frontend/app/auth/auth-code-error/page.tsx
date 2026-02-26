
import Link from 'next/link'

export default function AuthCodeError() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center p-4 text-center">
            <h1 className="text-2xl font-bold mb-4 text-red-500">인증 오류</h1>
            <p className="mb-6 text-gray-300">
                인증 코드를 확인하는 중 문제가 발생했습니다.<br />
                코드가 만료되었거나 이미 사용되었을 수 있습니다.
            </p>
            <Link
                href="/login"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
            >
                로그인 페이지로 이동
            </Link>
        </div>
    )
}
