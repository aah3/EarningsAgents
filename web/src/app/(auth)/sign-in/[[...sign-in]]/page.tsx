import { SignIn } from "@clerk/nextjs";
import { dark } from "@clerk/themes";

export default function SignInPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-[#0f1219]">
            <SignIn
                forceRedirectUrl="/dashboard"
                appearance={{
                    baseTheme: dark,
                    elements: {
                        card: "bg-[#191d29] border border-white/10 shadow-2xl",
                        headerTitle: "text-white font-outfit text-2xl",
                        headerSubtitle: "text-gray-400 font-medium",
                        socialButtonsBlockButton: "bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-colors",
                        formButtonPrimary: "bg-[#3366ff] text-white hover:bg-[#254bdb] font-bold",
                        footerActionLink: "text-[#3366ff] hover:text-[#254bdb]",
                        formFieldLabel: "text-gray-300 font-bold",
                        formFieldInput: "bg-white/5 border border-white/10 text-white focus:border-[#3366ff] focus:ring-1 focus:ring-[#3366ff]",
                        dividerText: "text-gray-500",
                        dividerLine: "bg-white/10",
                        footer: "hidden", // Hide the white footer at the bottom
                    },
                }}
            />
        </div>
    );
}
