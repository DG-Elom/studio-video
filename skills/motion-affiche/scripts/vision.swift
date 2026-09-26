// Analyse d'une affiche avec le framework Vision de macOS (aucun modèle à installer).
// Usage : swift vision.swift <image> <dossier-sortie>
// Écrit <sortie>/vision.json (textes + boîtes en pixels, origine en haut à gauche)
// et <sortie>/sujet-<n>.png (chaque sujet détouré, pleine taille, fond transparent).
import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 3 else { FileHandle.standardError.write("usage: vision.swift <image> <sortie>\n".data(using: .utf8)!); exit(2) }
let url = URL(fileURLWithPath: args[1])
let out = URL(fileURLWithPath: args[2], isDirectory: true)
try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)

guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
      let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print("image illisible"); exit(1) }
let W = Double(cg.width), H = Double(cg.height)

func px(_ r: CGRect) -> [Int] {
    [Int((r.minX * W).rounded()), Int(((1 - r.maxY) * H).rounded()), Int((r.width * W).rounded()), Int((r.height * H).rounded())]
}

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
let textReq = VNRecognizeTextRequest()
textReq.recognitionLevel = .accurate
textReq.recognitionLanguages = ["fr-FR", "en-US"]
textReq.usesLanguageCorrection = true
let fgReq = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([textReq, fgReq])

var texts: [[String: Any]] = []
for o in textReq.results ?? [] {
    guard let c = o.topCandidates(1).first else { continue }
    texts.append(["texte": c.string, "confiance": Double(c.confidence), "boite": px(o.boundingBox)])
}

let ci = CIContext()
var sujets: [[String: Any]] = []
if let fg = fgReq.results?.first {
    for inst in fg.allInstances.sorted() {
        let buf = try fg.generateMaskedImage(ofInstances: IndexSet(integer: inst), from: handler, croppedToInstancesExtent: false)
        let img = CIImage(cvPixelBuffer: buf)
        let f = out.appendingPathComponent("sujet-\(inst).png")
        guard let cgOut = ci.createCGImage(img, from: img.extent),
              let dest = CGImageDestinationCreateWithURL(f as CFURL, UTType.png.identifier as CFString, 1, nil) else { continue }
        CGImageDestinationAddImage(dest, cgOut, nil)
        CGImageDestinationFinalize(dest)
        sujets.append(["id": inst, "fichier": f.lastPathComponent])
    }
}

let json: [String: Any] = ["largeur": Int(W), "hauteur": Int(H), "textes": texts, "sujets": sujets]
let data = try JSONSerialization.data(withJSONObject: json, options: [.prettyPrinted, .sortedKeys])
try data.write(to: out.appendingPathComponent("vision.json"))
print("textes: \(texts.count) · sujets: \(sujets.count) → \(out.path)/vision.json")
