import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const sizes = [16, 32, 72, 96, 128, 144, 152, 192, 384, 512];
const inputSvg = path.join(__dirname, '../public/icons/icon.svg');
const outputDir = path.join(__dirname, '../public/icons');

async function generateIcons() {
  console.log('Generating icons from SVG...');

  for (const size of sizes) {
    const outputPath = path.join(outputDir, `icon-${size}x${size}.png`);

    await sharp(inputSvg)
      .resize(size, size)
      .png()
      .toFile(outputPath);

    console.log(`  Created: icon-${size}x${size}.png`);
  }

  // Also create feature graphic (1024x500) for Play Store
  const featureGraphicPath = path.join(outputDir, '../feature-graphic.png');

  // Create a feature graphic with the icon centered
  const featureGraphic = sharp({
    create: {
      width: 1024,
      height: 500,
      channels: 4,
      background: { r: 26, g: 54, b: 93, alpha: 1 } // #1a365d
    }
  });

  // Get the icon as a buffer
  const iconBuffer = await sharp(inputSvg)
    .resize(300, 300)
    .png()
    .toBuffer();

  // Composite the icon onto the feature graphic
  await featureGraphic
    .composite([
      {
        input: iconBuffer,
        left: 362, // (1024 - 300) / 2
        top: 100   // centered vertically
      }
    ])
    .png()
    .toFile(featureGraphicPath);

  console.log('  Created: feature-graphic.png');

  console.log('\nAll icons generated successfully!');
  console.log('\nNext steps:');
  console.log('1. Deploy to Vercel: npx vercel --prod');
  console.log('2. Go to https://pwabuilder.com');
  console.log('3. Enter your URL: https://notam-web.vercel.app');
  console.log('4. Download Android AAB package');
}

generateIcons().catch(console.error);
