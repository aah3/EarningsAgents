import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <SignIn appearance={{
                elements: {
                    card: "glass border border-white/5",
                    headerTitle: "text-white font-outfit",
                    headerSubtitle: "text-gray-400 font-medium",
                    socialButtonsBlockButton: "glass border border-white/5 text-white hover:bg-white/5",
                    formButtonPrimary: "bg-accent text-background hover:bg-accent/90 font-bold",
                    footerActionLink: "text-accent hover:text-accent/80",
                    formFieldLabel: "text-gray-400 font-bold",
                    formFieldInput: "glass border border-white/10 text-white focus:border-accent",
                }
            }} />
        </div>
    );
}
