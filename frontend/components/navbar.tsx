"use client"

import Link from "next/link"
import Image from "next/image"
import { useState } from "react"
import { Menu, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <nav className="w-full border-b bg-black">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        {/* Logo */}
        <div className="flex items-center">
          <Link href="/" className="flex items-center">
            <Image src="/Samplify.png" alt="Logo" width={200} height={200} />
          </Link>
        </div>

        {/* Desktop Navigation */}
        <div className="hidden items-center space-x-4 md:flex">
          <Button asChild size="sm" className="bg-black">
            <Link href="/" className="text-sm font-medium text-white "> HOME </Link>
          </Button>
          <Button asChild size="sm" className="bg-black">
            <Link href="/create" className="text-sm font-medium text-samplify-blue"> CREATE </Link> 
          </Button>
          <Button asChild size="sm" className="bg-black">
            <Link href="/login" className= "text-sm font-medium text-white"> LOGIN </Link>
          </Button>
        </div>

        {/* Mobile Menu Button */}
        <div className="flex md:hidden">
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <span className="sr-only">Open main menu</span>
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      <div className={cn("md:hidden", isMenuOpen ? "block" : "hidden")}>
        <div className="space-y-1 px-4 pb-3 pt-2 sm:px-3">
          <Link
            href="/"
            className="block rounded-md px-3 py-2 text-base font-medium text-white"
            onClick={() => setIsMenuOpen(false)}
          >
            Home
          </Link>
          <Link
            href="/create"
            className="block rounded-md px-3 py-2 text-base font-medium"
            style={{ color: "#73a4c4" }}
            onClick={() => setIsMenuOpen(false)}
          >
            Create
          </Link>
          <Link
            href="/login"
            className="block rounded-md px-3 py-2 text-base font-medium text-white"
            onClick={() => setIsMenuOpen(false)}
          >
            Login
          </Link>
        </div>
      </div>
    </nav>
  )
}

